import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.routers.health import router

def test_health_routes():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    assert client.get("/health/liveness").status_code == 200
    assert client.get("/health/readiness").json()["status"] == "ready"
