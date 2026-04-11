import pytest
from app.ai_infra.single_inference import InferenceRequest, perform_inference

@pytest.mark.asyncio
async def test_perform_inference():
    req = InferenceRequest(prompt="Hello")
    res = await perform_inference(None, req)
    
    assert "Hello" in res.output
    assert res.processed_time_ms >= 0
