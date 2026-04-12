from typing import AsyncIterator, List, Dict
from .base import LLMProvider
import httpx

class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "qwen2.5-coder:7b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system: str,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        # Placeholder for HTTPX async request logic
        if stream:
            async def _stream() -> AsyncIterator[str]:
                yield "Not implemented"
            return _stream()
        return "Not implemented"

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
