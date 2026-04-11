import pytest
import asyncio
from app.ai_infra.batch_inference import DynamicBatcher

@pytest.mark.asyncio
async def test_batcher_logic():
    batcher = DynamicBatcher(max_batch_size=2, wait_ms=10)
    await batcher.start(None)
    
    # Run two requests concurrently
    res1, res2 = await asyncio.gather(
        batcher.add("A"),
        batcher.add("B")
    )
    
    assert "Result for A" in res1
    assert "Result for B" in res2
    
    await batcher.stop()
