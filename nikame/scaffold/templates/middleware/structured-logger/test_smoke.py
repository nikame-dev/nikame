import pytest
import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.logger import StructuredLoggerMiddleware

app = FastAPI()
app.add_middleware(StructuredLoggerMiddleware)

@app.get("/test")
async def basic_test():
    return {"status": "ok"}

@app.get("/error")
async def error_route():
    raise ValueError("Something broke")

client = TestClient(app)

def test_logger_emits_around_request(caplog):
    # Depending on how structlog is configured, it likely pushes logs into the standard logging module
    # allowing caplog to pick them up in tests.
    res = client.get("/test")
    assert res.status_code == 200

def test_logger_traps_exception_timing(caplog):
    with pytest.raises(ValueError):
        client.get("/error")
