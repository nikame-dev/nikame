import httpx
import json
from typing import List, Optional, Dict, Any

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    async def list_models(self) -> List[str]:
        """List all models available in local Ollama instance."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [model['name'] for model in data.get('models', [])]
                return []
        except (httpx.ConnectError, httpx.TimeoutException):
            return []

    async def chat(self, model: str, messages: List[Dict[str, str]], stream: bool = False) -> Any:
        """Simple chat completion."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": stream
                }
            )
            if response.status_code == 200:
                if stream:
                    return response.aiter_lines()
                return response.json()
            response.raise_for_status()
