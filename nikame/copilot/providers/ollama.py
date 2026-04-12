import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    """Provider for Ollama local AI server."""

    def __init__(self, model: str = "qwen2.5-coder:7b", base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": stream,
            "options": {
                "temperature": 0.2,
            }
        }

        if stream:
            return self._stream_complete(payload)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return str(data["message"]["content"])

    async def _stream_complete(self, payload: dict[str, Any]) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self.base_url}/api/version")
                return resp.status_code == 200
        except Exception:
            return False

    @property
    def model_name(self) -> str:
        return self.model
