import time
from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge

# Custom metrics
INFERENCE_COUNT = Counter(
    "app_inference_total", 
    "Total number of AI inference calls",
    ["model_name"]
)

GPU_MEM_GAUGE = Gauge(
    "app_gpu_memory_usage_bytes",
    "Current GPU memory usage in bytes"
)

LATENCY_HISTOGRAM = Histogram(
    "app_inference_latency_seconds",
    "Latency of inference calls",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, float("inf")]
)

def setup_metrics(app: FastAPI):
    """
    Initializes Prometheus metrics and endpoints.
    Automatically exports HTTP metrics like request latency, 2xx/4xx/5xx counts.
    """
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
