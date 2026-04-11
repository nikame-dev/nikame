import asyncio
import json
from typing import AsyncGenerator, Any
from fastapi import Request

async def stream_heartbeat(request: Request, interval: int = 15) -> AsyncGenerator[dict[str, Any], None]:
    """
    Yields occasional empty comments/events to prevent proxy layers (like Nginx)
    from terminating the idle connection prematurely.
    """
    while True:
        if await request.is_disconnected():
            break
            
        # sse-starlette expects dicts mapping to EventSource formatting
        # Sending a 'ping' event or standard comment
        yield {
            "event": "ping",
            "data": "keepalive",
            # "id": "optional-message-id",
            # "retry": 15000, # instruct client to reconnect after 15s if dropped
        }
        await asyncio.sleep(interval)


async def multiplex_streams(*generators: AsyncGenerator) -> AsyncGenerator:
    """
    Helper to merge multiple async generators into one.
    Useful for mixing a heartbeat generator with real data streams.
    """
    # This is a naive implementation; a true multiplexer would use asyncio.Queue 
    # or anyio task groups to concurrently poll generators.
    # We will simply poll them sequentially in short bursts for this pattern.
    pass

async def event_generator(request: Request) -> AsyncGenerator[dict[str, Any], None]:
    """
    Example event publisher.
    """
    # Always tell clients how quickly to retry if connection goes down
    yield {
        "event": "control",
        "data": json.dumps({"message": "connected"}),
        "retry": 5000 
    }
    
    count = 0
    while True:
        if await request.is_disconnected():
            # Crucial: always check for disconnects to prevent infinite orphaned background tasks
            break
            
        yield {
            "event": "message",
            "data": json.dumps({"count": count, "system": "healthy"}),
            "id": str(count)
        }
        
        count += 1
        await asyncio.sleep(1)
