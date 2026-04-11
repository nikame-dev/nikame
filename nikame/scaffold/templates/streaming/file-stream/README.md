# Large File Streaming

A drop-in pattern for serving large static files safely and efficiently without loading their entire content into memory.

## Usage

1. Configure `DATA_DIR` to point to your storage location.
2. Mount the router:

```python
from app.routers.files import router as files_router
app.include_router(files_router)
```

## Why it matters

FastAPI uses `anyio` to read files asynchronously. By yielding chunks, the server remains responsive and can handle thousands of concurrent downloads with minimal RAM overhead.

## Gotchas

- **OS Limits**: Ensure your serving environment has sufficient file descriptors configured if you expect high concurrency.
- **Headers**: This module manually sets `Content-Length`. Ensure your storage backend provides accurate file sizes.
