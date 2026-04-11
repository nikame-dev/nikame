# JWT Bearer Authentication

A drop-in, zero-edit JWT authentication module for FastAPI. It provides endpoints for login, handles token parsing, and gives you a `get_current_user` dependency to protect your routes.

## Usage

1. Mount the router in your FastAPI app:
```python
from app.routers.auth import router as auth_router

app.include_router(auth_router)
```

2. Protect your endpoints:
```python
from fastapi import APIRouter, Depends
from app.auth.jwt import get_current_user

router = APIRouter()

@router.get("/protected")
async def protected_route(user_id: str = Depends(get_current_user)):
    return {"message": f"Hello User {user_id}"}
```

## Setup & Configuration
You will need to substitute standard token variables:
* `SECRET_KEY`
* `ALGORITHM` (usually HS256)
* `ACCESS_TOKEN_EXPIRE_MINUTES`

These should ideally be loaded from environment variables using `pydantic-settings`.

## Gotchas
* We use OAuth2PasswordBearer which reads from the `Authorization: Bearer <token>` header. It specifically expects the login endpoint to accept form data (an OAuth2 quirk required by Swagger UI).
* We do not include the user model definition. The implementation provides a stub where you should hook in your actual database fetch logic.
