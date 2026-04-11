import logging
from text_generation import AsyncClient
from typing import AsyncGenerator, List, Optional

logger = logging.getLogger("app.ai_infra.tgi")

class TGIClient:
    """
    Client for Hugging Face Text-Generation-Inference (TGI) servers.
    """
    def __init__(self, base_url: str = "{{TGI_URL}}" or "http://localhost:8080"):
        self.client = AsyncClient(base_url)

    async def generate(self, prompt: str, max_new_tokens: int = 512, **kwargs) -> str:
        """
        Non-streaming generation.
        """
        response = await self.client.generate(prompt, max_new_tokens=max_new_tokens, **kwargs)
        return response.generated_text

    async def stream(self, prompt: str, max_new_tokens: int = 512, **kwargs) -> AsyncGenerator[str, None]:
        """
        Native TGI streaming.
        """
        async for response in self.client.generate_stream(prompt, max_new_tokens=max_new_tokens, **kwargs):
            if not response.token.special:
                yield response.token.text

tgi_client = TGIClient()
