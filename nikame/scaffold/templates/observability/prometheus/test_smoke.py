import pytest
from fastapi import FastAPI
from app.observability.metrics import setup_metrics

def test_metrics_setup():
    app = FastAPI()
    setup_metrics(app)
    # Verify the /metrics route is added
    routes = [r.path for r in app.routes]
    assert "/metrics" in routes
