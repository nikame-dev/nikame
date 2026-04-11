import pytest
from fastapi import FastAPI, Security
from fastapi.testclient import TestClient
from app.auth.api_key import require_api_key

app = FastAPI()

@app.get("/secure-endpoint")
async def secure_endpoint(user: str = Security(require_api_key)):
    return {"user": user}

client = TestClient(app)

def test_missing_api_key():
    response = client.get("/secure-endpoint")
    assert response.status_code == 401
    assert "missing" in response.json().get("detail", "")

def test_invalid_api_key():
    response = client.get("/secure-endpoint", headers={"X-API-Key": "invalid-key"})
    assert response.status_code == 401
    assert "invalid" in response.json().get("detail", "")

def test_valid_api_key_header():
    response = client.get("/secure-endpoint", headers={"X-API-Key": "test-key-123"})
    assert response.status_code == 200
    assert response.json()["user"] == "system-user"

def test_valid_api_key_query():
    response = client.get("/secure-endpoint?api_key=prod-key-456")
    assert response.status_code == 200
    assert response.json()["user"] == "external-service"
