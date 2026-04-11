import pytest
from fastapi import FastAPI
from app.observability.tracing import setup_tracing

def test_tracing_setup():
    app = FastAPI()
    # verify setup doesn't crash even if collector is missing
    setup_tracing(app)
    pass
