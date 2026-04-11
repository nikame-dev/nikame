import pytest
import os
from app.streaming.file_stream import file_chunk_generator

@pytest.mark.asyncio
async def test_file_chunk_generator(tmp_path):
    # Create a dummy file
    test_file = tmp_path / "test.dat"
    content = b"x" * (2 * 1024 * 1024) # 2MB
    test_file.write_bytes(content)
    
    chunks = []
    async for chunk in file_chunk_generator(str(test_file), chunk_size=1024*1024):
        chunks.append(chunk)
        
    assert len(chunks) == 2
    assert b"".join(chunks) == content
