# Model Loader

A production pattern for managing heavy machine learning models in FastAPI. 

## Importance

Loading a model (like Llama, Stable Diffusion, or BERT) can take several seconds and gigabytes of RAM. You never want to load it inside a request handler. Instead, load it once at startup and keep it in memory.

## Usage

1. Mount the lifespan in your `main.py`:

```python
from app.ai_infra.model_loader import model_lifespan
app = FastAPI(lifespan=model_lifespan)
```

2. Access the model in your routes via dependency injection:

```python
from app.ai_infra.model_loader import get_model

@app.post("/predict")
async def predict(model: Any = Depends(get_model)):
    # use model here
    pass
```

## Gotchas

- **VRAM Leakage**: Ensure you properly clear GPU cache (e.g., `torch.cuda.empty_cache()`) during unload if you are doing frequent hot-reloads.
- **Worker Processes**: If running with Gunicorn (`--workers > 1`), each worker will load its own copy of the model, potentially exceeding your VRAM. Consider using a single worker for AI services if VRAM is limited.
