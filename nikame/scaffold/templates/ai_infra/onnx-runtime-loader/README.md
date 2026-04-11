# ONNX Runtime Loader

Provides high-performance inference using **ONNX Runtime**, the industry standard for cross-platform ML deployment.

## Why ONNX?

-   **Speed**: Faster than standard PyTorch/TensorFlow in many CPU environments.
-   **Portability**: One model format for Python, C++, and Web.
-   **Optimization**: Automatic graph fusions and constant folding.

## Usage

1. Convert your model to `.onnx` format.
2. Initialize in `lifespan`:

```python
from app.ai_infra.onnx_loader import ONNXModelManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = ONNXModelManager(model_path="model.onnx")
    await manager.load()
    app.state.model = manager
    yield
```

## Gotchas

-   **Providers**: To use GPU, you must install `onnxruntime-gpu` and have the correct CUDA/cuDNN versions. The standard `onnxruntime` is CPU-only.
-   **Input Shapes**: ONNX is stricter about input shapes than PyTorch. Ensure your pre-processing produces exactly what the model expects.
