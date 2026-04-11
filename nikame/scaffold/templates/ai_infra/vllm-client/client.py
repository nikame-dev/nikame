import logging
from openai import AsyncOpenAI
from typing import AsyncGenerator, Dict, Any, Optional

logger = logging.getLogger("app.ai_infra.vllm")

class VLLMClient:
    """
    OpenAI-compatible client for connecting to a local or remote vLLM server.
    """
    def __init__(self, base_url: str = "{{VLLM_URL}}" or "http://localhost:8000/v1", api_key: str = "{{VLLM_API_KEY}}" or "token-abc"):
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key
        )

    async def generate(self, model: str, prompt: str, **kwargs) -> str:
        """
        Non-streaming generation.
        """
        response = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content

    async def stream(self, model: str, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        Streaming generation.
        """
        response = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **kwargs
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

vllm_client = VLLMClient()
