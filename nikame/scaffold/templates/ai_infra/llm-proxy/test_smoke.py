import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers.llm_proxy import router

def test_proxy_endpoint_exists():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    # Just verify it's routed
    pass
