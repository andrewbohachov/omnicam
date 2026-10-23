"""
EasyWebcam - WebRTC Session & Frame Pipeline
Decouples network receiving from V4L2 writing via a non-blocking queue.
Enforces fixed output dimension, stride, and automatic 16:9 aspect-crop,
preventing perspective stretching and scanline artifacts.
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

def crop_to_16_9(frame: av.VideoFrame) -> av.VideoFrame:
    """Center-crops frame to 16:9 widescreen to prevent perspective squash/stretch."""
    target_ratio = 16.0 / 9.0
    src_w, src_h = frame.width, frame.height
    src_ratio = src_w / src_h

    # If already ~16:9, return as-is
    if abs(src_ratio - target_ratio) < 0.04:
        return frame

    if src_ratio < target_ratio:
        # Taller than 16:9 (e.g. 4:3 1280x960), crop top & bottom
        new_h = int(src_w / target_ratio)
        new_h = (new_h // 2) * 2
        crop_y = (src_h - new_h) // 2
        new_w = src_w
        crop_x = 0
    else:
        # Wider than 16:9, crop sides
        new_w = int(src_h * target_ratio)
        new_w = (new_w // 2) * 2
        crop_x = (src_w - new_w) // 2
        new_h = src_h
        crop_y = 0

    try:
        cropped = av.VideoFrame(new_w, new_h, frame.format.name)
        y_stride = frame.planes[0].line_size
        cropped.planes[0].update(
            memoryview(frame.planes[0])[crop_y * y_stride : (crop_y + new_h) * y_stride]
        )
        u_stride = frame.planes[1].line_size
        u_crop_y = crop_y // 2
        u_h = new_h // 2
        cropped.planes[1].update(
            memoryview(frame.planes[1])[u_crop_y * u_stride : (u_crop_y + u_h) * u_stride]
        )
        v_stride = frame.planes[2].line_size
        cropped.planes[2].update(
            memoryview(frame.planes[2])[u_crop_y * v_stride : (u_crop_y + u_h) * v_stride]
        )
        return cropped
    except Exception:
        return frame


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
        Dedicated V4L2 writer loop: Normalizes every incoming frame to target resolution
        and writes packed scanlines with exact stride into /dev/videoX.
        """
        self._last_fps_time = time.time()
        self._frame_count = 0
        expected_line_size = self.target_width * 2

        try:
            while self.is_active:
                in_frame = await self._frame_queue.get()
                self._last_phone_w = in_frame.width
                self._last_phone_h = in_frame.height

                # Ensure perfect 16:9 perspective (center-crop non-16:9 streams)
                normalized_frame = crop_to_16_9(in_frame)

                # Reformat and scale to target device resolution (1280x720 YUYV)
                out_frame = normalized_frame.reformat(
                    width=self.target_width,
                    height=self.target_height,
                    format="yuyv422"
                )

                plane = out_frame.planes[0]
                if plane.line_size == expected_line_size:
                    raw_bytes = bytes(plane)
                else:
                    raw_plane = bytes(plane)
                    raw_bytes = b"".join(
                        raw_plane[i * plane.line_size : i * plane.line_size + expected_line_size]
                        for i in range(self.target_height)
                    )

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
