# Hugging Face Pipeline

A high-level wrapper for Hugging Face `transformers.pipeline`, optimized for FastAPI production use.

## Features

-   **Auto-Device Selection**: Automatically detects and uses CUDA (NVIDIA), MPS (Apple Silicon), or CPU.
-   **VRAM Efficient**: Uses `torch.float16` by default on CUDA devices.
-   **Lifespan Friendly**: Designed to be initialized once during application startup.

## Usage

1. Configure `PIPELINE_TASK` (e.g., `text-generation`, `summarization`, `sentiment-analysis`) and `HF_MODEL_NAME`.
2. Initialize in your `lifespan`:

```python
from app.ai_infra.hf_pipeline import HFPipelineManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = HFPipelineManager(task="text-generation", model_name="gpt2")
    await manager.load()
    app.state.model = manager
    yield
```

## Gotchas

-   **Model Size**: Large models (7B+ parameters) require significant VRAM. Check your GPU capacity before loading.
-   **Concurrency**: While the pipeline wrapper is thread-safe, the underlying GPU call is serial. Use the **GPU Semaphore** pattern to limit concurrent access.
