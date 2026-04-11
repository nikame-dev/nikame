# Structured Logger Middleware

Integrates FastAPI with `structlog` to emit completely uniform JSON logs across the application. 

Instead of printing loose text like `HTTP GET /ping completed`, this outputs rigorous dictionaries that indexing services (Datadog, Elastic, CloudWatch) can instantly parse.

## Usage

Mount it into your main factory or `main.py`:

```python
from fastapi import FastAPI
from app.middleware.logger import StructuredLoggerMiddleware

app = FastAPI()
app.add_middleware(StructuredLoggerMiddleware)
```

## Setup

It is highly recommended you install the `structlog-setup` observability module first to configure structlog's core formatting pipelines.

## Gotchas

* Logs are structured but default to Python's console format if `structlog` hasn't been explicitly configured to emit canonical JSON.
* Ensure you add this middleware fairly high up the stack so logic that crashes during initialization gets safely logged.
