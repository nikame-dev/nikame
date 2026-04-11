import json
from typing import AsyncGenerator
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

# Initialize client - in production this should be in a dependency
client = AsyncOpenAI(api_key="{{OPENAI_API_KEY}}")

async def get_openai_stream(prompt: str) -> AsyncGenerator[str, None]:
    """
    Calls OpenAI and yields chunks as they arrive.
    Wraps the response in SSE format.
    """
    stream = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            # Yielding in SSE format: data: <payload>\n\n
            yield f"data: {json.dumps({'content': content})}\n\n"
    
    yield "data: [DONE]\n\n"
