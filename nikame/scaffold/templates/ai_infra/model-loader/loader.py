import logging
from typing import Any, Optional
from fastapi import FastAPI, Request, Depends
from contextlib import asynccontextmanager

# In a real app, you'd import torch or transformers here
# import torch

logger = logging.getLogger("app.ai_infra.model_loader")

class ModelManager:
    """
    Handles the lifecycle of a heavy ML model.
    """
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.model: Optional[Any] = None

    async def load(self):
        logger.info(f"Loading model: {self.model_id}...")
        # Simulate heavy loading
        # self.model = AutoModel.from_pretrained(self.model_id)
        self.model = {"id": self.model_id, "status": "loaded"} 
        logger.info("Model loaded successfully.")

    async def unload(self):
        logger.info(f"Unloading model: {self.model_id}...")
        self.model = None
        # if torch.cuda.is_available(): torch.cuda.empty_cache()

def get_model(request: Request) -> Any:
    """
    Dependency to access the loaded model from app state.
    """
    model_manager: ModelManager = request.app.state.model_manager
    if not model_manager.model:
        raise RuntimeError("Model is not loaded")
    return model_manager.model

@asynccontextmanager
async def model_lifespan(app: FastAPI):
    """
    Lifespan context manager for model management.
    """
    model_id = "{{MODEL_ID}}"
    manager = ModelManager(model_id)
    await manager.load()
    app.state.model_manager = manager
    
    yield
    
    await manager.unload()
