from typing import Dict, List, Set
from fastapi import WebSocket

class ConnectionManager:
    """
    Manages active WebSocket connections, supporting broadcast and room-based messaging.
    """
    def __init__(self):
        # active_connections: tracks all active websockets
        self.active_connections: List[WebSocket] = []
        # rooms: maps room_id to a set of connected WebSockets
        self.rooms: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str = "default"):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str = "default"):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if room_id in self.rooms:
            self.rooms[room_id].discard(websocket)
            if not self.rooms[room_id]:
                del self.rooms[room_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, room_id: str = "default"):
        """Sends a message to all clients in a specific room."""
        if room_id in self.rooms:
            for connection in self.rooms[room_id]:
                await connection.send_text(message)

# Global instances usually defined here or in dependencies
manager = ConnectionManager()
