# WebSocket Manager

A production-ready connection manager for handling bidirectional real-time communication in FastAPI.

## Usage

1. Mount the router:
```python
from app.routers.websockets import router as ws_router
app.include_router(ws_router)
```

2. Clients connect to `ws://localhost:8000/ws/{room_id}`.

## Features

- **Room Based**: Group connections by `room_id` automatically.
- **Broadcast**: Send messages to all users in a specific room.
- **Auto Cleanup**: Handles `WebSocketDisconnect` cleanly to prevent memory leaks.

## Gotchas

- **Scaling**: This implementation is **in-memory**. If you run multiple workers (gunicorn/uvicorn) or horizontal instances, clients won't see messages from other processes. Use Redis Pub/Sub for cross-process communication.
- **Stickiness**: Ensure your load balancer supports sticky sessions or WebSocket upgrades.
