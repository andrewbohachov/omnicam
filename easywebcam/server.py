"""
EasyWebcam - Local Web Server & Signaling
Serves mobile web client over HTTPS, coordinates WebRTC signaling,
and maintains bidirectional WebSocket control link.
"""

import json
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
        self.ws_clients = set()
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_get("/", self._handle_index)
        self.app.router.add_post("/offer", self._handle_offer)
        self.app.router.add_get("/ws", self._handle_ws)
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

    async def _handle_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.ws_clients.add(ws)
        try:
            async for msg in ws:
                pass
        finally:
            self.ws_clients.discard(ws)
        return ws

    async def broadcast_command(self, action: str, value=None):
        """Dispatches command to phone via WebRTC DataChannel and WebSocket."""
        # Try DataChannel first
        dc_sent = self.session.send_control_command(action, value)

        # Broadcast via WebSocket
        payload = json.dumps({"action": action, "value": value})
        for ws in list(self.ws_clients):
            try:
                await ws.send_str(payload)
            except Exception:
                pass

    async def cleanup(self):
        for ws in list(self.ws_clients):
            try:
                await ws.close()
            except Exception:
                pass
        self.ws_clients.clear()
        await self.session.close()
        self.sink.stop()
