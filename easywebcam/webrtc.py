"""
EasyWebcam - WebRTC Session & Frame Pipeline
Receives video track from phone browser, decodes frames with PyAV, and pipes them to V4L2DeviceManager.
"""

import asyncio
import time
from typing import Optional, Callable
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
import av
from .v4l2 import V4L2DeviceManager

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

        self.pc = RTCPeerConnection()
        self.is_active = True

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
