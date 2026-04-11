import pytest
def test_onnx_init():
    from app.ai_infra.onnx_loader import ONNXModelManager
    manager = ONNXModelManager(model_path="dummy.onnx")
    assert manager.model_path == "dummy.onnx"
