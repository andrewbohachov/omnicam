"""
EasyWebcam - WebRTC Session & Frame Pipeline
Receives video track from phone browser, decodes frames with PyAV, and pipes them to V4L2DeviceManager.
Includes Python 3.14 asyncio compatibility patches for aioice/aiortc.
"""

import asyncio
import time
import sys
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

class WebRTCSession:
    def __init__(self, sink: V4L2DeviceManager, on_stats_update: Optional[Callable[[dict], None]] = None):
        self.sink = sink
        self.pc: Optional[RTCPeerConnection] = None
        self.on_stats_update = on_stats_update
        self.is_active = False
        self._current_width = 0
        self._current_height = 0
        self.fps = 0.0
        self.total_frames = 0
        self._frame_count = 0
        self._last_fps_time = time.time()

    async def handle_offer(self, sdp: str, sdp_type: str) -> dict:
        """Processes client WebRTC SDP offer and returns server answer."""
        if self.pc:
            await self.close()

        # No external STUN servers needed for local LAN streaming
        config = RTCConfiguration(iceServers=[])
        self.pc = RTCPeerConnection(configuration=config)
        self.is_active = True

        # Prioritize hardware-accelerated H.264 video codec
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
                asyncio.create_task(self._process_video_track(track))

        offer = RTCSessionDescription(sdp=sdp, type=sdp_type)
        await self.pc.setRemoteDescription(offer)
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)

        return {
            "sdp": self.pc.localDescription.sdp,
            "type": self.pc.localDescription.type
        }

    async def _process_video_track(self, track: MediaStreamTrack):
        """Continuously reads frames from WebRTC track and writes to V4L2."""
        self._last_fps_time = time.time()
        self._frame_count = 0

        try:
            while self.is_active:
                frame: av.VideoFrame = await track.recv()
                w, h = frame.width, frame.height

                # Configure format on resolution change
                if w != self._current_width or h != self._current_height:
                    self._current_width = w
                    self._current_height = h
                    self.sink.setup_format(w, h, pixel_format="YUYV")

                # Reformat to YUYV (hardware-accelerated via FFmpeg/PyAV)
                yuyv_frame = frame.reformat(format="yuyv422")
                raw_bytes = bytes(yuyv_frame.planes[0])
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
                            "width": self._current_width,
                            "height": self._current_height,
                            "frames": self.total_frames
                        })
        except Exception:
            pass
        finally:
            self.is_active = False

    async def close(self):
        """Closes current WebRTC peer connection."""
        self.is_active = False
        if self.pc:
            try:
                await self.pc.close()
            except Exception:
                pass
            self.pc = None
