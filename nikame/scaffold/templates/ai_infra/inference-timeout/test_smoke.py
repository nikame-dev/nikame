import pytest
import asyncio
from app.ai_infra.reliability import with_inference_reliability, InferenceTimeoutError

@pytest.mark.asyncio
async def test_reliability_timeout():
    
    @with_inference_reliability(timeout_seconds=0.1, max_retries=1)
    async def slow_func():
        await asyncio.sleep(0.5)
        return "done"

    with pytest.raises(InferenceTimeoutError):
        await slow_func()

@pytest.mark.asyncio
async def test_reliability_success():
    
    @with_inference_reliability(timeout_seconds=1.0)
    async def fast_func():
        return "ok"

    assert await fast_func() == "ok"
