# GGUF llama-cpp

Provides support for loading and serving quantized LLMs in the **GGUF** format using `llama-cpp-python`.

## Why GGUF?

GGUF is the successor to GGML. It is highly optimized for **consumer hardware**:
-   **Macbooks**: Full Metal acceleration support.
-   **CPU-Only Servers**: Extremely fast inference compared to standard PyTorch.
-   **VRAM Constrained GPUs**: Allows "splitting" the model between VRAM and RAM.

## Usage

1. Download a GGUF model (e.g., from TheBloke on Hugging Face).
2. Set `GGUF_MODEL_PATH` in your environment.
3. Initialize in `lifespan`:

```python
from app.ai_infra.gguf_loader import GGUFModelManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = GGUFModelManager(n_gpu_layers=35) # -1 for all layers on GPU
    await manager.load()
    app.state.model = manager
    yield
```

## Gotchas

-   **Installation**: `llama-cpp-python` requires a C++ compiler. For GPU support, you must install it with specialized environment variables:
    -   CUDA: `CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python`
    -   Metal: `CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python`
-   **Context Window**: `n_ctx` defaults to 512 in many versions. Ensure you set it high enough for your use case.
