# Global Error Boundary

A global catch-all middleware preventing traceback leaks.

In many web frameworks by default, an uncaught internal `Exception` or `ValueError` outputs the full stack trace to the client so the developer knows what broke. In Production, leaking module paths and code execution flow to arbitrary clients is a critical risk.

## Usage

You must mount this *very* early in application loading (so it wraps the entire app scope).

```python
from fastapi import FastAPI
from app.middleware.boundary import ErrorBoundaryMiddleware

app = FastAPI()

app.add_middleware(ErrorBoundaryMiddleware)
```
