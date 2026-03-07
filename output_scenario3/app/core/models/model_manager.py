"""
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
        self.models = [{'name': 'llm', 'url': 'http://llm:8000/v1', 'source': 'huggingface'}]
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(self, model_name: str, messages: List[dict], **kwargs) -> ModelResponse:
        """Generic OpenAI-compatible chat completion."""
        model = next((m for m in self.models if m["name"] == model_name), None)
        if not model:
            raise ValueError(f"Model {model_name} not configured")
        
        response = await self.client.post(
            f"{model['url']}/chat/completions",
            json={
                "model": model_name,
                "messages": messages,
                **kwargs
            }
        )
        response.raise_for_status()
        data = response.json()
        return ModelResponse(
            text=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {})
        )

model_manager = ModelManager()
