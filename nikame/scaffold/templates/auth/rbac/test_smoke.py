import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from app.auth.rbac import require_role
from app.core.error_handlers import ForbiddenException

app = FastAPI()

# Exception handler to actually return 403 on ForbiddenException in the test
@app.exception_handler(ForbiddenException)
async def forbidden_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=403, content={"detail": exc.detail})

@app.get("/admin")
async def admin_route(user=Depends(require_role("admin"))):
    return {"status": "ok"}

@app.get("/user")
async def user_route(user=Depends(require_role("user"))):
    return {"status": "ok"}

client = TestClient(app)

def test_rbac_user_accesses_admin_route_fails():
    # Because our dummy stub always returns a "user" role, the admin route should fail
    response = client.get("/admin")
    assert response.status_code == 403

def test_rbac_user_accesses_user_route_succeeds():
    # Because our dummy stub always returns a "user" role, this should work
    response = client.get("/user")
    assert response.status_code == 200
