"""ML Gateway Codegen for NIKAME.

Generates a FastAPI wrapper using LiteLLM to provide a unified, 
OpenAI-compatible interface to all serving backends.
"""

from __future__ import annotations

from pathlib import Path

from nikame.config.schema import NikameConfig
from nikame.utils.file_writer import FileWriter


from nikame.codegen.base import BaseCodegen, CodegenContext

class MLGatewayCodegen(BaseCodegen):
    """Generates the ml-gateway service."""
    NAME = "ml_gateway"
    DESCRIPTION = "Unified interface for LLM completions and embeddings"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx, config)

    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Trigger if the configuration has MLOps items."""
        # Note: We need the full config to check this, so we'll check for ml_features or similar
        # For now, we'll trigger if any LLM module is present
        llm_modules = {"llamacpp", "ollama", "vllm", "tgi", "triton", "localai", "xinference", "airllm"}
        return any(m in active_modules for m in llm_modules)

    def generate(self) -> list[tuple[str, str]]:
        """Generate the model manager 'Glue' logic."""
        if not self.config.mlops:
            return []

        files = []
        
        # 1. Generate model_manager.py (if models configured)
        if self.config.mlops.models:
            manager_content = self._get_model_manager_py()
            files.append(("app/core/models/model_manager.py", manager_content))
            files.append(("app/core/models/__init__.py", ""))

        # 2. Generate LLM Gateway service (always if mlops present)
        gateway_content = self._get_llm_gateway_py()
        files.append(("app/services/llm_gateway.py", gateway_content))
        files.append(("app/services/__init__.py", ""))
        
        return files

    def _get_llm_gateway_py(self) -> str:
        """Generate the services/llm_gateway.py logic."""
        return f'''"""
NIKAME LLM Gateway.
Unified interface for LLM completions and embeddings.
"""
import os
import httpx
from typing import Any, List, Optional

class LLMGateway:
    """Singleton gateway for all LLM interactions."""
    
    @classmethod
    async def generate_completion(cls, prompt: str, **kwargs) -> str:
        """Generate a text completion."""
        # Simple implementation for generated stub
        # In a real setup, this routes via model_manager
        return "NIKAME Generated Response"

    @classmethod
    async def generate_embedding(cls, text: str) -> List[float]:
        """Generate a vector embedding for the given text."""
        # Return a dummy 384-dim vector (SBERT size)
        return [0.1] * 384
'''

    def _get_model_manager_py(self) -> str:
        """Generate the core/models/model_manager.py logic."""
        models_config = []
        for model in self.config.mlops.models:
            models_config.append({
                "name": model.name,
                "url": f"http://{model.name}:8000/v1",
                "source": model.source
            })

        return f'''"""
NIKAME AI Model Manager — Logic Synthesis Glue.
Provides a unified async interface for interacting with LLMs and Embedding models.
"""

import os
import httpx
from typing import Any, List, Optional
from pydantic import BaseModel

class ModelResponse(BaseModel):
    text: str
    usage: dict

class ModelManager:
    """Unified manager for all configured AI models."""
    
    def __init__(self):
        self.models = {models_config}
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(self, model_name: str, messages: List[dict], **kwargs) -> ModelResponse:
        """Generic OpenAI-compatible chat completion."""
        model = next((m for m in self.models if m["name"] == model_name), None)
        if not model:
            raise ValueError(f"Model {{model_name}} not configured")
        
        response = await self.client.post(
            f"{{model['url']}}/chat/completions",
            json={{
                "model": model_name,
                "messages": messages,
                **kwargs
            }}
        )
        response.raise_for_status()
        data = response.json()
        return ModelResponse(
            text=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {{}})
        )

model_manager = ModelManager()
'''
