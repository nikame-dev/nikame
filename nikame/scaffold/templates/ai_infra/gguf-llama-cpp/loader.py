import logging
import os
from llama_cpp import Llama
from typing import Any, Dict, Optional

logger = logging.getLogger("app.ai_infra.gguf")

class GGUFModelManager:
    """
    Manages a llama-cpp-python Llama instance for GGUF models.
    Supports CPU-only and GPU offloading.
    """
    def __init__(self, model_path: str = "{{GGUF_MODEL_PATH}}", n_gpu_layers: int = -1):
        self.model_path = model_path
        self.n_gpu_layers = n_gpu_layers
        self.llm = None

    async def load(self):
        if not os.path.exists(self.model_path):
            logger.error(f"GGUF model not found at: {self.model_path}")
            raise FileNotFoundError(self.model_path)
            
        logger.info(f"Loading GGUF model: {self.model_path} with {self.n_gpu_layers} GPU layers...")
        
        # This is a CPU-intensive/blocking call, but safe in lifespan
        self.llm = Llama(
            model_path=self.model_path,
            n_gpu_layers=self.n_gpu_layers,
            n_ctx=2048,
            verbose=False
        )
        logger.info("GGUF model loaded successfully.")

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Run inference.
        """
        output = self.llm(
            prompt,
            max_tokens=kwargs.get("max_tokens", 128),
            stop=kwargs.get("stop", ["\n"]),
            echo=False
        )
        return output["choices"][0]["text"]
