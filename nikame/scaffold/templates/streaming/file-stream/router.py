from fastapi import APIRouter
from app.streaming.file_stream import get_streaming_file_response

router = APIRouter(prefix="/files", tags=["Streaming"])

@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Endpoint to download large files via streaming.
    """
    return get_streaming_file_response(filename)
