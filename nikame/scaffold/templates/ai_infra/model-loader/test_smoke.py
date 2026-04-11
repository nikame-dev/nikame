import pytest
from fastapi import FastAPI
from app.ai_infra.model_loader import ModelManager

@pytest.mark.asyncio
async def test_model_manager_lifecycle():
    manager = ModelManager("test/model")
    assert manager.model is None
    
    await manager.load()
    assert manager.model is not None
    assert manager.model["id"] == "test/model"
    
    await manager.unload()
    assert manager.model is None
