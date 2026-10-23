"""
EasyWebcam - Local Web Server & Signaling
Serves mobile web client over HTTPS and coordinates WebRTC signaling.
"""

from aiohttp import web
from pathlib import Path
from .v4l2 import V4L2DeviceManager
from .webrtc import WebRTCSession

STATIC_DIR = Path(__file__).parent / "static"

class EasyWebcamServer:
    def __init__(self, sink: V4L2DeviceManager, on_stats_update=None):
        self.sink = sink
        self.session = WebRTCSession(sink, on_stats_update=on_stats_update)
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_get("/", self._handle_index)
        self.app.router.add_post("/offer", self._handle_offer)
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

    async def cleanup(self):
        await self.session.close()
        self.sink.stop()
