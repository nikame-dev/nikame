import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers.oauth2 import router as oauth2_router
from urllib.parse import urlparse

app = FastAPI()
app.include_router(oauth2_router)

client = TestClient(app)

def test_login_redirect():
    response = client.get("/auth/oauth2/login/google", follow_redirects=False)
    # 307 Temporary Redirect is used by default for RedirectResponse in FastAPI
    assert response.status_code in (307, 302, 303)
    
    redirect_url = response.headers["location"]
    parsed = urlparse(redirect_url)
    assert parsed.netloc == "accounts.google.com"
    assert "client_id" in parsed.query

def test_callback_requires_code():
    # Will fail pydantic validation if code is missing
    response = client.get("/auth/oauth2/callback/google")
    assert response.status_code == 422
    assert "Field required" in response.text
