import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.boundary import ErrorBoundaryMiddleware

app = FastAPI()
app.add_middleware(ErrorBoundaryMiddleware)

@app.get("/crash")
async def crash_route():
    # Simulate a deep core system completely failing unexpectedly
    1 / 0
    return {"status": "ok"}

client = TestClient(app)

def test_error_boundary_hides_traceback():
    # If the app crashes, test client will generally throw if unhandled by middleware
    # Because of our middleware, it should cleanly return a JSON response with a 500 status code
    res = client.get("/crash")
    
    assert res.status_code == 500
    
    data = res.json()
    assert "error" in data
    assert data["error"] == "Internal Server Error"
    
    # We explicitly check that python internals did not leak out
    assert "ZeroDivisionError" not in res.text
    assert "traceback" not in res.text.lower()
