import pytest
import time
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.latency import LatencyTimerMiddleware

app = FastAPI()
app.add_middleware(LatencyTimerMiddleware)

@app.get("/fast")
async def fast_route():
    return {"status": "ok"}

@app.get("/slow")
async def slow_route():
    await asyncio.sleep(0.1)
    return {"status": "ok"}

client = TestClient(app)

def test_fast_request_has_header():
    res = client.get("/fast")
    assert res.status_code == 200
    assert "X-Process-Time" in res.headers
    
    val = float(res.headers["X-Process-Time"])
    assert val > 0.0
    assert val < 0.1 # Should be practically instant

def test_slow_request_is_timed_accurately():
    res = client.get("/slow")
    assert res.status_code == 200
    assert "X-Process-Time" in res.headers
    
    val = float(res.headers["X-Process-Time"])
    assert val >= 0.1 # Sleep is at least 0.1s
