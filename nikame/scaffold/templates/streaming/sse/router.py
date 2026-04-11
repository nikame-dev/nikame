from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from app.streaming.sse import event_generator

router = APIRouter(prefix="/stream", tags=["Streaming"])

@router.get("/events")
async def sse_endpoint(request: Request):
    """
    Returns an unending Server-Sent Events stream to the client.
    """
    # EventSourceResponse automatically sets the text/event-stream content type
    # and disables browser caching headers correctly.
    return EventSourceResponse(event_generator(request))
