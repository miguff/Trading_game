import asyncio
from fastapi import WebSocket
from typing import Any, Dict, List
import json

class WebSocketManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def send_json(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        await websocket.send_text(json.dumps(message))

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        message = {"type": event_type, "payload": payload}
        async with self._lock:
            websockets = list(self.active_connections)
        for connection in websockets:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                await self.disconnect(connection)
