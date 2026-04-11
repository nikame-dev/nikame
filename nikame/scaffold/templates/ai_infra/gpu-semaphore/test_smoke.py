import pytest
import asyncio
from app.ai_infra.gpu_semaphore import InferenceSemaphore

@pytest.mark.asyncio
async def test_semaphore_limit():
    limiter = InferenceSemaphore(1)
    
    # First acquisition succeeds
    await limiter.acquire()
    assert limiter.semaphore.locked()
    
    # Second acquisition would hang, so we use a timeout
    try:
        await asyncio.wait_for(limiter.acquire(), timeout=0.1)
        pytest.fail("Should have timed out")
    except asyncio.TimeoutError:
        pass
    
    limiter.release()
    assert not limiter.semaphore.locked()
