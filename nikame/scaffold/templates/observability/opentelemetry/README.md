# OpenTelemetry Tracing

Implements distributed tracing for your FastAPI application.

## Why Tracing?

In a microservice or AI-heavy architecture, a single user request might go through:
`Load Balancer -> FastAPI -> Redis -> GPU worker -> Database`

Tracing allows you to see the **entire journey** of that request, pinpointing exactly where slowness is occurring (e.g., "The model took 8s but the database took only 5ms").

## Usage

1. Initialize in `main.py`:
```python
from app.observability.tracing import setup_tracing
setup_tracing(app, service_name="ai-api")
```

2. Run an OTLP collector (like Jaeger):
```bash
docker run -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest
```

## Gotchas

-   **Performance Overhead**: Heavy tracing can add minor latency. In production, use a **Sampler** (e.g., `ParentBased(root=TraceIdRatioBased(0.1))`) to only trace 10% of requests.
-   **Context Propagation**: To trace across multiple services (e.g., into a Celery worker), you must manually propagate the `traceparent` header.
-   **Dependencies**: This module specifically uses the `gRPC` exporter. Ensure your collector supports OTLP/gRPC.
