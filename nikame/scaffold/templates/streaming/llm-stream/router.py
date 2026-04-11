from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.streaming.llm_stream import get_openai_stream

router = APIRouter(prefix="/llm", tags=["Streaming"])

@router.get("/stream")
async def stream_llm(prompt: str = "Hello!"):
    """
    Endpoints that streams back LLM responses using Server-Sent Events.
    """
    return StreamingResponse(
        get_openai_stream(prompt),
        media_type="text/event-stream"
    )
