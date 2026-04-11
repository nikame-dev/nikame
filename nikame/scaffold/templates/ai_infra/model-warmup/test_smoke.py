import pytest
import asyncio
from app.ai_infra.warmup import run_model_warmup

@pytest.mark.asyncio
async def test_warmup_execution():
    called = 0
    async def mock_inference(model, inp):
        nonlocal called
        called += 1
        return "ok"

    await run_model_warmup(None, mock_inference, ["test1", "test2"], iterations=2)
    
    # 2 inputs * 2 iterations = 4 calls
    assert called == 4
