import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from app.middleware.cors import setup_cors

@pytest.fixture
def app_prod():
    app = FastAPI()
    setup_cors(app, environment="prod", origins=["https://allowed.com"])
    
    @app.get("/")
    def read_root():
        return {"hello": "world"}
        
    return app

@pytest.fixture
def app_dev():
    app = FastAPI()
    setup_cors(app, environment="dev")
    
    @app.get("/")
    def read_root():
        return {"hello": "world"}
        
    return app

def test_cors_dev_allows_all(app_dev):
    client = TestClient(app_dev)
    
    # Preflight Options request
    headers = {
        "Origin": "http://evil.com",
        "Access-Control-Request-Method": "GET"
    }
    res = client.options("/", headers=headers)
    assert res.headers.get("access-control-allow-origin") == "*"

def test_cors_prod_denies_evil_origin(app_prod):
    client = TestClient(app_prod)
    
    # Preflight from unallowed origin
    headers = {
        "Origin": "http://evil.com",
        "Access-Control-Request-Method": "GET"
    }
    res = client.options("/", headers=headers)
    assert res.status_code == 400  # Starlette CORS blocks it completely

def test_cors_prod_allows_configured_origin(app_prod):
    client = TestClient(app_prod)
    
    headers = {
        "Origin": "https://allowed.com",
        "Access-Control-Request-Method": "GET"
    }
    res = client.options("/", headers=headers)
    assert res.headers.get("access-control-allow-origin") == "https://allowed.com"
