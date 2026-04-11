import httpx
import json
import logging
from typing import AsyncGenerator
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger("app.ai_infra.proxy")

OPENAI_API_KEY = "{{OPENAI_API_KEY}}"
OPENAI_BASE_URL = "{{OPENAI_BASE_URL}}" or "https://api.openai.com/v1"

async def proxy_llm_request(request: Request) -> StreamingResponse:
    """
    Proxies a chat completion request to OpenAI while capturing metrics.
    """
    client = httpx.AsyncClient()
    
    # Clone headers but remove Host and inject our API key
    headers = dict(request.headers)
    headers.pop("host", None)
    headers["authorization"] = f"Bearer {OPENAI_API_KEY}"
    
    # Read the incoming body
    body = await request.json()
    is_stream = body.get("stream", False)

    # Prepare the proxy request
    proxy_req = client.build_request(
        "POST",
        f"{OPENAI_BASE_URL}/chat/completions",
        json=body,
        headers=headers,
        timeout=60.0
    )

    if not is_stream:
        # Simple non-streaming pass-through
        resp = await client.send(proxy_req)
        return StreamingResponse(
            resp.aiter_raw(),
            status_code=resp.status_code,
            headers=dict(resp.headers)
        )

    # Streaming pass-through
    async def stream_generator():
        async with client.stream("POST", f"{OPENAI_BASE_URL}/chat/completions", json=body, headers=headers) as resp:
            async for chunk in resp.aiter_raw():
                yield chunk
        await client.aclose()

    return StreamingResponse(stream_generator(), media_type="text/event-stream")
