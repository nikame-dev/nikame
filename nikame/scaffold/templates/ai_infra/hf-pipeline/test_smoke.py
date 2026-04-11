import pytest
from app.ai_infra.hf_pipeline import HFPipelineManager

def test_device_detection():
    # Just verify the helper runs without crashing
    from app.ai_infra.hf_pipeline import get_device
    device = get_device()
    assert device in ["cuda", "mps", "cpu"]
