import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.request_id import RequestIDMiddleware, get_request_id

app = FastAPI()
app.add_middleware(RequestIDMiddleware)

@app.get("/id")
async def get_id():
    return {"id": get_request_id()}

client = TestClient(app)

def test_request_id_generated():
    res = client.get("/id")
    assert res.status_code == 200
    
    # Must be in headers
    assert "X-Request-ID" in res.headers
    
    # Must match inner context route payload that read the variable
    assert res.json()["id"] == res.headers["X-Request-ID"]

def test_request_id_preserved_when_passed():
    given_id = "external-proxy-uuid-1234"
    res = client.get("/id", headers={"X-Request-ID": given_id})
    assert res.status_code == 200
    assert res.headers["X-Request-ID"] == given_id
    assert res.json()["id"] == given_id
