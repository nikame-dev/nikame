import ollama
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional

logger = logging.getLogger("app.ai_infra.ollama")

class OllamaClient:
    """
    Async client for Ollama, supporting chat and vision models.
    """
    def __init__(self, host: str = "{{OLLAMA_HOST}}" or "http://localhost:11434"):
        self.client = ollama.AsyncClient(host=host)

    async def chat(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Simple non-streaming chat.
        """
        return await self.client.chat(model=model, messages=messages, **kwargs)

    async def stream(self, model: str, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """
        Streaming chat response.
        """
        async for part in await self.client.chat(model=model, messages=messages, stream=True, **kwargs):
            yield part['message']['content']

    async def vision(self, model: str, prompt: str, images: List[bytes]) -> str:
        """
        Support for vision models (like llava).
        """
        response = await self.client.generate(model=model, prompt=prompt, images=images)
        return response['response']

ollama_client = OllamaClient()
