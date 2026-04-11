# TGI Client

A specialized client for interacting with Hugging Face **Text-Generation-Inference (TGI)** servers.

## Why TGI?

TGI is Hugging Face's official production serving solution. It features:
-   **Continuous Batching**: High throughput.
-   **Flash Attention & Paged Attention**: Optimized inference kernels.
-   **Safetensors Support**: Fast model loading.

## Usage

```python
from app.ai_infra.tgi_client import tgi_client

@app.post("/generate")
async def generate(prompt: str):
    return await tgi_client.generate(prompt, max_new_tokens=256)
```

## Gotchas

-   **Tokenization**: TGI does tokenization server-side. You don't need a local tokenizer.
-   **Streaming**: TGI streaming uses a specialized protocol. Use the `stream()` method to consume tokens as they arrive.
