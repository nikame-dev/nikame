# Inference Reliability (Timeout & Retry)

AI models are notoriously unpredictable. They can hang, crash the GPU driver, or experience transient hardware latencies. This pattern ensures your API remains stable by enforcing hard timeouts and intelligent retries.

## Why it matters

Without a timeout, a hanging model call will hold an HTTP connection open indefinitely, eventually exhausting your server's worker pool. Retries with **Exponential Backoff** ensure that if the GPU is momentarily busy or swapping VRAM, the request eventually succeeds without manual user intervention.

## Usage

### Using the Decorator

```python
from app.ai_infra.reliability import with_inference_reliability

@with_inference_reliability(timeout_seconds=60.0, max_retries=3)
async def my_load_balancing_call(prompt: str):
    return await heavy_model.generate(prompt)
```

### Using the Helper

```python
from app.ai_infra.reliability import safe_inference_call

@app.post("/predict")
async def predict_route(data: str):
    return await safe_inference_call(model.generate(data), timeout=10.0)
```

## Gotchas

-   **Idempotency**: Only retry operations that are safe to repeat. Inference is typically idempotent, but ensure your state doesn't leak between attempts.
-   **Cascading Failure**: If your GPU is dying, retrying 3 times across 100 concurrent requests will actually increase the load and make the failure worse. Use this in conjunction with the **Circuit Breaker** pattern.
