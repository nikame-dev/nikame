import pytest
from app.ai_infra.arq_worker.worker import process_inference

@pytest.mark.asyncio
async def test_worker_function():
    # Context is usually provided by ARQ, we pass dummy
    ctx = {}
    result = await process_inference(ctx, "hello")
    assert "hello" in result
