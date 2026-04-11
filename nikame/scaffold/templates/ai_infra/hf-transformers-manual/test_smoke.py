import pytest
# Testing transformers models requires heavy downloads, we skip actual loading here.

def test_manual_structure():
    from app.ai_infra.hf_manual import HFModelManager
    manager = HFModelManager("gpt2")
    assert manager.model_name == "gpt2"
