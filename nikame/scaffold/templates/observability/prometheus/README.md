# Prometheus Metrics

Provides comprehensive monitoring for your FastAPI application and AI inference pipelines.

## Features

-   **HTTP Metrics**: Automatic tracking of request counts, latency (p50, p90, p99), and status codes via `Instrumentator`.
-   **Custom AI Metrics**:
    -   `app_inference_total`: Track how many inferences are being performed per model.
    -   `app_inference_latency_seconds`: High-resolution histograms of your ML models' performance.
    -   `app_gpu_memory_usage_bytes`: Real-time tracking of VRAM consumption.

## Usage

1. Initialize in `main.py`:
```python
from app.observability.metrics import setup_metrics
setup_metrics(app)
```

2. Record custom metrics in your code:
```python
from app.observability.metrics import INFERENCE_COUNT, LATENCY_HISTOGRAM

INFERENCE_COUNT.labels(model_name="llama3").inc()
with LATENCY_HISTOGRAM.time():
    # run inference
    pass
```

3. Access metrics at `http://localhost:8000/metrics`.

## Gotchas

-   **Cardinality**: Avoid adding labels with high cardinality (like `user_id`) to your metrics, as this can overwhelm your Prometheus server.
-   **Security**: The `/metrics` endpoint is public by default. In production, ensure it is only accessible via your internal network or protected by basic auth.
