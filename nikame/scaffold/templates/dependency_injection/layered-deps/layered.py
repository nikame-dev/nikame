"""
Layered dependency injection chain.

Demonstrates how to build a robust chain of dependencies where each
links to the next. For example, validating an admin user requires:
  Request -> DB Session -> Token Extraction -> User Lookup -> Role Verification
"""
from typing import AsyncGenerator, Callable, Any

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel


# ─── Mocks for Demonstration ──────────────────────────────────────────────
class User(BaseModel):
    id: int
    username: str
    role: str

class MockSession:
    async def get_user(self, user_id: int) -> User | None:
        if user_id == 1:
            return User(id=1, username="admin", role="admin")
        return User(id=user_id, username="user", role="user")


# ─── Layer 1: Infrastructure ──────────────────────────────────────────────
async def get_db() -> AsyncGenerator[MockSession, None]:
    """Provides a database session scoped to the request lifecycle."""
    session = MockSession()
    try:
        yield session
    finally:
        pass  # Close session


# ─── Layer 2: Authentication ──────────────────────────────────────────────
async def get_current_token(request: Request) -> str:
    """Extracts and initially validates the raw authentication token."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token",
        )
    return auth_header.split(" ")[1]


# ─── Layer 3: Identity Verification ───────────────────────────────────────
async def get_current_user(
    token: str = Depends(get_current_token),
    db: MockSession = Depends(get_db),
) -> User:
    """Uses the token and db to resolve the actual User entity."""
    # Mock token decoding
    if token == "invalid":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired",
        )
    
    # Mock lookup
    user_id = 1 if token == "admin_token" else 2
    user = await db.get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
        
    return user


# ─── Layer 4: Authorization Factory ───────────────────────────────────────
def require_role(required_role: str) -> Callable[[User], User]:
    """
    Dependency factory for role-based access control.
    Returns a dependency that verifies the user has the required role.
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires {required_role} privileges",
            )
        return user
        
    return role_checker


# Example Usage (Do not include in router directly like this in production):
# @router.get("/admin", dependencies=[Depends(require_role("admin"))])
# async def admin_dashboard():
#     ...
