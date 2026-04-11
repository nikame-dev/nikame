# vLLM Client

A specialized client for interacting with **vLLM** servers using the OpenAI-compatible API.

## Why vLLM?

vLLM is currently the industry standard for high-throughput LLM serving. It uses **PagedAttention** to manage KV-caches, allowing for significantly higher concurrency than standard Hugging Face implementations.

## Usage

Connecting to a vLLM server running on Docker or a separate VM:

```python
from app.ai_infra.vllm_client import vllm_client

@app.post("/generate")
async def generate(prompt: str):
    # This is a network call to the vLLM server
    return await vllm_client.generate(
        model="meta-llama/Llama-2-7b-hf", 
        prompt=prompt
    )
```

## Gotchas

-   **Model Names**: Ensure the `model` string matches exactly what the vLLM server was started with.
-   **Timeout**: vLLM instances can occasionally hang or experience "garbage collection" delays. Use the **Inference Timeout** pattern when calling this client.
