# Gunicorn Configuration

A production-ready Gunicorn configuration optimized for FastAPI and Uvicorn.

## Why use Gunicorn in production?

While `uvicorn` is a great ASGI server, it lacks the robustness of a process manager. `gunicorn` acts as a "parent" process that monitors, spawns, and restarts `uvicorn` workers if they crash or hang.

## Key Features

1.  **Dynamic Concurrency**: Automatically calculates the number of workers based on the CPU cores available in the environment.
2.  **Configurable Timeouts**: Default 120s timeout to accommodate slower AI model inference.
3.  **Environment Driven**: Most settings can be overridden via standard environment variables (`PORT`, `WEB_CONCURRENCY`, `LOG_LEVEL`).

## Usage

In your Dockerfile or startup script:
```bash
gunicorn -c gunicorn_conf.py main:app
```

## Gotchas

-   **Memory Usage**: Each worker is a separate process. If your model uses 4GB of RAM and you have 4 workers, you need 16GB of total system RAM.
-   **VRAM**: Similar to RAM, workers do NOT share VRAM. You will likely hit OOM (Out of Memory) errors if multiple workers try to load a large model. For AI deployments, often `WEB_CONCURRENCY=1` is the only safe choice on a single GPU.
