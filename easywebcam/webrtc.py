"""
EasyWebcam - WebRTC Session & Frame Pipeline
Decouples network receiving from V4L2 writing via a non-blocking queue.
Enforces fixed output dimension and stride with intelligent Aspect-Fit (Pillarboxing/Letterboxing),
guaranteeing 100% natural, undistorted proportions in both Horizontal and Vertical orientations.
"""

import asyncio
import time
import json
from typing import Optional, Callable
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, MediaStreamTrack
from aiortc.rtcrtpreceiver import RTCRtpReceiver
import av
from .v4l2 import V4L2DeviceManager

# --- Compatibility Patches for Python 3.14 & aioice ---
try:
    import asyncio.selector_events
    _orig_fatal = asyncio.selector_events._SelectorDatagramTransport._fatal_error
    def _safe_fatal(self, exc, message='Fatal error on transport'):
        if getattr(self, '_loop', None) is None:
            return
        _orig_fatal(self, exc, message)
    asyncio.selector_events._SelectorDatagramTransport._fatal_error = _safe_fatal
except Exception:
    pass

try:
    import aioice.ice
    import aioice.stun

    _orig_send_stun = aioice.ice.StunProtocol.send_stun
    def _safe_send_stun(self, message, addr):
        if not self.transport or getattr(self.transport, '_sock', None) is None:
            return
        try:
            _orig_send_stun(self, message, addr)
        except Exception:
            pass
    aioice.ice.StunProtocol.send_stun = _safe_send_stun

    _orig_retry = aioice.stun.Transaction._Transaction__retry
    def _safe_retry(self):
        try:
            _orig_retry(self)
        except Exception:
            pass
    aioice.stun.Transaction._Transaction__retry = _safe_retry
except Exception:
    pass
# -----------------------------------------------------

def render_frame_aspect_fit(in_frame: av.VideoFrame, target_w: int, target_h: int) -> bytes:
    """
    Renders the incoming frame (landscape OR portrait) into target_w x target_h YUYV.
    Preserves exact aspect ratio:
    - Landscape: fills the widescreen display.
    - Portrait: centers the vertical image with clean black pillarbox bars on the sides.
    Zero geometric distortion or stretching!
    """
    src_w, src_h = in_frame.width, in_frame.height

    # Calculate proportional scale
    scale = min(target_w / src_w, target_h / src_h)
    # Align scaled dimensions to multiples of 4 (ensures YUYV 2-pixel macroblock alignment)
    scaled_w = (int(src_w * scale) // 4) * 4
    scaled_h = (int(src_h * scale) // 2) * 2

    # Direct match (e.g. 1920x1080 -> 1920x1080)
    if scaled_w == target_w and scaled_h == target_h:
        out_frame = in_frame.reformat(width=target_w, height=target_h, format="yuyv422")
        plane = out_frame.planes[0]
        expected_stride = target_w * 2
        if plane.line_size == expected_stride:
            return bytes(plane)
        raw_plane = bytes(plane)
        return b"".join(
            raw_plane[i * plane.line_size : i * plane.line_size + expected_stride]
            for i in range(target_h)
        )

    # Scale with aspect preservation and center blit with clean black bars
    scaled_frame = in_frame.reformat(width=scaled_w, height=scaled_h, format="yuyv422")
    scaled_plane = bytes(scaled_frame.planes[0])

    # CRITICAL: Read each scanline using actual FFmpeg stride (which includes alignment padding)
    src_stride = scaled_frame.planes[0].line_size
    bytes_to_copy = scaled_w * 2
    target_stride = target_w * 2

    # Center offsets
    pad_x = ((target_w - scaled_w) // 4) * 2
    pad_y = (target_h - scaled_h) // 2
    start_byte_x = pad_x * 2

    # Create solid black YUYV canvas (Y=0, U=128, Y=0, V=128)
    black_line = b"\x00\x80\x00\x80" * (target_w // 2)
    canvas = bytearray(black_line * target_h)

    for y in range(scaled_h):
        c_off = (pad_y + y) * target_stride + start_byte_x
        f_off = y * src_stride
        canvas[c_off : c_off + bytes_to_copy] = scaled_plane[f_off : f_off + bytes_to_copy]

    return bytes(canvas)


class WebRTCSession:
    def __init__(self, sink: V4L2DeviceManager, on_stats_update: Optional[Callable[[dict], None]] = None):
        self.sink = sink
        self.target_width = sink.target_width
        self.target_height = sink.target_height
        self.pc: Optional[RTCPeerConnection] = None
        self.channel = None
        self.on_stats_update = on_stats_update
        self.is_active = False
        self.fps = 0.0
        self.total_frames = 0
        self._frame_count = 0
        self._last_fps_time = time.time()
        self._last_phone_w = 0
        self._last_phone_h = 0
        self._frame_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        self._writer_task: Optional[asyncio.Task] = None

    async def handle_offer(self, sdp: str, sdp_type: str) -> dict:
        """Processes client WebRTC SDP offer and returns server answer."""
        if self.pc:
            await self.close()

        config = RTCConfiguration(iceServers=[])
        self.pc = RTCPeerConnection(configuration=config)
        self.is_active = True
        self._frame_queue = asyncio.Queue(maxsize=1)

        try:
            self.channel = self.pc.createDataChannel("control")
        except Exception:
            self.channel = None

        try:
            t = self.pc.addTransceiver("video", direction="recvonly")
            capabilities = RTCRtpReceiver.getCapabilities("video")
            if capabilities and capabilities.codecs:
                h264_codecs = [c for c in capabilities.codecs if "h264" in c.mimeType.lower()]
                other_codecs = [c for c in capabilities.codecs if "h264" not in c.mimeType.lower()]
                t.setCodecPreferences(h264_codecs + other_codecs)
        except Exception:
            pass

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            state = self.pc.connectionState if self.pc else "closed"
            if state in ["failed", "closed", "disconnected"]:
                self.is_active = False

        @self.pc.on("track")
        def on_track(track: MediaStreamTrack):
            if track.kind == "video":
                self._writer_task = asyncio.create_task(self._v4l2_writer_loop())
                asyncio.create_task(self._network_receiver_loop(track))

        offer = RTCSessionDescription(sdp=sdp, type=sdp_type)
        await self.pc.setRemoteDescription(offer)
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)

        return {
            "sdp": self.pc.localDescription.sdp,
            "type": self.pc.localDescription.type
        }

    def send_control_command(self, action: str, value=None) -> bool:
        """Sends control message to the phone via WebRTC DataChannel."""
        if self.channel and self.channel.readyState == "open":
            try:
                payload = json.dumps({"action": action, "value": value})
                self.channel.send(payload)
                return True
            except Exception:
                pass
        return False

    async def _network_receiver_loop(self, track: MediaStreamTrack):
        """
        Dedicated network loop: Reads packets from the WebRTC socket with zero delay.
        """
        try:
            while self.is_active:
                frame: av.VideoFrame = await track.recv()
                if self._frame_queue.full():
                    try:
                        self._frame_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                self._frame_queue.put_nowait(frame)
        except Exception:
            pass
        finally:
            self.is_active = False

    async def _v4l2_writer_loop(self):
        """
        Dedicated V4L2 writer loop: Normalizes every incoming frame (portrait or landscape)
        into target resolution with guaranteed aspect ratio preservation.
        """
        self._last_fps_time = time.time()
        self._frame_count = 0

        try:
            while self.is_active:
                in_frame = await self._frame_queue.get()
                self._last_phone_w = in_frame.width
                self._last_phone_h = in_frame.height

                # Render with exact aspect ratio fit (Pillarbox vertical / Fullscreen horizontal)
                raw_bytes = render_frame_aspect_fit(in_frame, self.target_width, self.target_height)
                self.sink.write_frame(raw_bytes)

                self.total_frames += 1
                self._frame_count += 1
                now = time.time()
                elapsed = now - self._last_fps_time
                if elapsed >= 1.0:
                    self.fps = round(self._frame_count / elapsed, 1)
                    self._frame_count = 0
                    self._last_fps_time = now
                    if self.on_stats_update:
                        self.on_stats_update({
                            "fps": self.fps,
                            "phone_w": self._last_phone_w,
                            "phone_h": self._last_phone_h,
                            "out_w": self.target_width,
                            "out_h": self.target_height,
                            "frames": self.total_frames
                        })
        except Exception:
            pass
        finally:
            self.is_active = False

    async def close(self):
        """Closes current WebRTC peer connection and worker tasks."""
        self.is_active = False
        if self._writer_task:
            self._writer_task.cancel()
            self._writer_task = None
        if self.pc:
            try:
                await self.pc.close()
            except Exception:
                pass
            self.pc = None
            self.channel = None
