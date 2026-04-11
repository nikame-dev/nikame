# Batch Inference

Implements **Dynamic Batching**. Instead of running one inference call per request, this pattern buffers multiple requests and runs them as a single batch on the GPU.

## Why it matters

GPUs reach peak efficiency when processing multiple items at once. Running a batch of 8 often takes only slightly longer than running 1, effectively increasing your system's throughput by 8x.

## Usage

1. Initialize in `app.state` during lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    batcher = DynamicBatcher(max_batch_size=8, wait_ms=50)
    await batcher.start(model)
    app.state.batcher = batcher
    yield
    await batcher.stop()
```

2. Use in your route:

```python
@app.post("/predict")
async def predict_batch(input_data: str, request: Request):
    return await request.app.state.batcher.add(input_data)
```

## Gotchas

- **Latency Tradeoff**: We wait up to `wait_ms` (e.g., 50ms) to fill a batch. This adds a tiny bit of latency to low-traffic requests but provides massive throughput for high-traffic ones.
- **Error Propagation**: If the model fails specifically on one item in the batch, typically the entire batch fails unless you catch errors per-item inside the worker.
- **Timeout**: Ensure your client handles the worst-case latency (wait_ms + inference_time).
