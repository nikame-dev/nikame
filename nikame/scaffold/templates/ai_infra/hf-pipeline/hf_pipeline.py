import logging
import torch
from transformers import pipeline
from typing import Any, Dict, Optional

logger = logging.getLogger("app.ai_infra.hf_pipeline")

def get_device() -> str:
    """
    Auto-detect the best available device.
    """
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"

class HFPipelineManager:
    """
    Manages a Hugging Face pipeline lifecycle.
    """
    def __init__(self, task: str, model_name: str, model_kwargs: Optional[Dict[str, Any]] = None):
        self.task = task
        self.model_name = model_name
        self.model_kwargs = model_kwargs or {}
        self.pipe = None

    async def load(self):
        device = get_device()
        logger.info(f"Loading HF pipeline '{self.task}' with '{self.model_name}' on {device}...")
        
        # Use float16 for GPU to save VRAM
        dtype = torch.float16 if device == "cuda" else torch.float32
        
        self.pipe = pipeline(
            task=self.task,
            model=self.model_name,
            device=device,
            torch_dtype=dtype,
            **self.model_kwargs
        )
        logger.info("HF pipeline loaded successfully.")

    async def __call__(self, *args, **kwargs):
        """
        Allows calling the manager directly to use the pipeline.
        """
        if not self.pipe:
            raise RuntimeError("Pipeline not loaded")
        return self.pipe(*args, **kwargs)
