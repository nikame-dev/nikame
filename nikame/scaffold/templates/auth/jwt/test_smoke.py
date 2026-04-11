import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from app.auth.jwt import create_access_token, get_current_user
from app.routers.auth import router as auth_router

app = FastAPI()
app.include_router(auth_router)

@app.get("/test-protected")
async def protected_route(user_id: str = Depends(get_current_user)):
    return {"status": "ok", "user": user_id}

client = TestClient(app)

def test_login():
    response = client.post("/auth/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_protected_route_unauthorized():
    response = client.get("/test-protected")
    assert response.status_code == 401

def test_protected_route_authorized():
    access_token = create_access_token(subject="123")
    response = client.get(
        "/test-protected", 
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"] == "123"
