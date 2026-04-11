# Single Inference

A standardized pattern for handling single-item (synchronous) AI model inference. 

## Workflow

1. **Validation**: Pydantic strictly validates the `InferenceRequest` input shape.
2. **Locking**: The `Depends(get_gpu_lock)` ensures this request only runs when GPU capacity is available.
3. **Inference**: The `perform_inference` function cleanly separates API logic from ML logic.

## Usage

Mount the router:

```python
from app.routers.inference import router as ai_router
app.include_router(ai_router)
```

## Gotchas

- **Blocking Calls**: If your model call is truly CPU-blocking (sync), wrap it in `run_in_executor` to avoid freezing the event loop.
