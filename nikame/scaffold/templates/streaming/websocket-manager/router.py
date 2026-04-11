from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.streaming.websocket_manager import manager

router = APIRouter(prefix="/ws", tags=["Streaming"])

@router.websocket("/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()
            # Echo back to everyone in the room
            await manager.broadcast(f"Room {room_id} message: {data}", room_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        await manager.broadcast(f"Client left room {room_id}", room_id)
