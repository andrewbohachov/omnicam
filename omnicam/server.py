"""
OmniCam - Local Web Server & Signaling
Serves mobile web client over HTTPS, coordinates WebRTC signaling,
and maintains instant command delivery to the smartphone.
"""

import asyncio
import json
from aiohttp import web
from pathlib import Path
from .v4l2 import V4L2DeviceManager
from .webrtc import WebRTCSession

STATIC_DIR = Path(__file__).parent / "static"

class OmniCamServer:
    def __init__(self, sink: V4L2DeviceManager, on_stats_update=None):
        self.sink = sink
        self.session = WebRTCSession(sink, on_stats_update=on_stats_update)
        self.app = web.Application()
        self.command_queue = asyncio.Queue()
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_get("/", self._handle_index)
        self.app.router.add_post("/offer", self._handle_offer)
        self.app.router.add_get("/poll-command", self._handle_poll_command)
        self.app.router.add_static("/static", str(STATIC_DIR))

    async def _handle_index(self, request):
        index_file = STATIC_DIR / "index.html"
        return web.FileResponse(index_file)

    async def _handle_offer(self, request):
        params = await request.json()
        sdp = params.get("sdp")
        sdp_type = params.get("type", "offer")
        if not sdp:
            return web.json_response({"error": "Missing sdp"}, status=400)

        answer = await self.session.handle_offer(sdp, sdp_type)
        return web.json_response(answer)

    async def _handle_poll_command(self, request):
        """Long-polling endpoint for 100% reliable command delivery to mobile browser."""
        try:
            cmd = await asyncio.wait_for(self.command_queue.get(), timeout=20.0)
            return web.json_response(cmd)
        except asyncio.TimeoutError:
            return web.json_response({"action": "ping"})

    async def broadcast_command(self, action: str, value=None):
        """Delivers command via WebRTC DataChannel AND instant HTTP polling."""
        self.session.send_control_command(action, value)
        await self.command_queue.put({"action": action, "value": value})

    async def cleanup(self):
        await self.session.close()
        self.sink.stop()
