# GPU Semaphore

Prevents your server from crashing due to Out-Of-Memory (OOM) errors by strictly limiting how many inference calls can happen simultaneously.

## Importance

GPUs have a fixed amount of VRAM. If you attempt to run 10 large language model inferences at once on a single consumer GPU, the driver will likely crash with an OOM error. The semaphore acts as a traffic light, allowing only `MAX_CONCURRENT_INFERENCE` requests to enter the "active GPU" section at any time.

## Usage

Protect your heavy routes with the `get_gpu_lock` dependency:

```python
from app.ai_infra.gpu_semaphore import get_gpu_lock

@app.post("/v1/generate", dependencies=[Depends(get_gpu_lock)])
async def generate_text(prompt: str):
    # Only N requests will ever be inside this function body at once
    return await my_model.run(prompt)
```

## Gotchas

- **Queue Depth**: If your GPU is busy, incoming requests will "hang" indefinitely at the `Depends(get_gpu_lock)` step. To avoid user frustration, consider adding a timeout in the semaphore logic that returns a `503 Service Unavailable` with a `Retry-After` header if the queue is too long.
