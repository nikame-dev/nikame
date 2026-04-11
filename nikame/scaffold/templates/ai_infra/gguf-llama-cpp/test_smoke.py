import pytest
def test_gguf_init():
    from app.ai_infra.gguf_loader import GGUFModelManager
    manager = GGUFModelManager(model_path="dummy.gguf")
    assert manager.model_path == "dummy.gguf"
