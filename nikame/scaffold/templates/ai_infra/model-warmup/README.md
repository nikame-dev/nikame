# Model Warmup

Eliminates "Cold Start" latency for your machine learning models.

## Why it matters

When you load a model (especially using libraries like PyTorch or ONNX Runtime), the first time you run inference, the system often performs lazy initialization:
-   CUDA kernels are compiled or loaded into the GPU.
-   Memory offsets are cached.
-   Graph optimizations are finalized.

This causes the **first** request to be 5-10x slower than subsequent requests. By running dummy inputs through the model during startup, your real users get peak performance immediately.

## Usage

Integrate into your app shutdown/startup (lifespan):

```python
from app.ai_infra.warmup import run_model_warmup
from app.ai_infra.single_inference import perform_inference

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Load Model
    await manager.load()
    
    # 2. Warmup
    await run_model_warmup(
        manager.model, 
        perform_inference, 
        warmup_inputs=[{"prompt": "test"}],
        iterations=2
    )
    
    yield
```

## Gotchas

-   **Startup Time**: Warmup adds to your application's boot time. In Kubernetes, ensure your `initialDelaySeconds` for Readiness probes is long enough to accommodate loading + warmup.
-   **Resource Usage**: Warmup uses GPU/CPU resources. Ensure your environment has the overhead for this during deployment.
