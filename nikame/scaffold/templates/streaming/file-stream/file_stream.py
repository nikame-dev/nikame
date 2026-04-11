import os
from typing import AsyncGenerator
import anyio
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

DATA_DIR = "{{DATA_DIR}}" # e.g. "/var/data" or "./uploads"

async def file_chunk_generator(file_path: str, chunk_size: int = 1024 * 1024) -> AsyncGenerator[bytes, None]:
    """
    Read a file in chunks asynchronously to avoid blocking the event loop.
    Default chunk size: 1MB.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    async with await anyio.open_file(file_path, mode="rb") as f:
        while True:
            chunk = await f.read(chunk_size)
            if not chunk:
                break
            yield chunk

def get_streaming_file_response(filename: str) -> StreamingResponse:
    """
    Returns a StreamingResponse for a large file.
    Includes proper content-disposition headers for downloads.
    """
    full_path = os.path.join(DATA_DIR, filename)
    
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File does not exist")
        
    return StreamingResponse(
        file_chunk_generator(full_path),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(os.path.getsize(full_path))
        }
    )
