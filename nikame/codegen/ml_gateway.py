"""ML Gateway Codegen for NIKAME.

Generates a FastAPI wrapper using LiteLLM to provide a unified, 
OpenAI-compatible interface to all serving backends.
"""

from __future__ import annotations

from pathlib import Path

from nikame.config.schema import NikameConfig
from nikame.utils.file_writer import FileWriter


class MLGatewayCodegen:
    """Generates the ml-gateway service."""

    def __init__(self, config: NikameConfig) -> None:
        self.config = config

    def generate(self, output_dir: Path) -> None:
        """Generate the model manager 'Glue' logic."""
        if not self.config.mlops or not self.config.mlops.models:
            return

        writer = FileWriter(output_dir)
        
        # 1. Generate model_manager.py
        manager_content = self._get_model_manager_py()
        writer.write_file("app/core/models/model_manager.py", manager_content)
        writer.write_file("app/core/models/__init__.py", "")

        # 2. Add dependencies to requirements.txt if needed
        # (Actually init.py handles requirements aggregation from components/features)

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

