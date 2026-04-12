import httpx
import json
from typing import List, Optional, Dict, Any, AsyncIterator

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
        """Simple chat completion (non-streaming)."""
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                }
            )
            if response.status_code == 200:
                return response.json()
            response.raise_for_status()

    async def chat_stream(self, model: str, messages: List[Dict[str, str]], options: Dict[str, Any] = None) -> AsyncIterator[str]:
        """Streaming chat completion — yields tokens as they arrive."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if options:
            payload["options"] = options

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if "message" in data:
                            content = data["message"].get("content", "")
                            if content:
                                yield content
                        if data.get("done"):
                            return
                    except json.JSONDecodeError:
                        continue
