from typing import List, Callable
from fastapi import Depends
from app.auth.jwt import get_current_user
from app.core.error_handlers import ForbiddenException

# A standard role hierarchy where upper roles inherit permissions of lower roles
# For example, an admin has all permissions of a user, plus more.
ROLE_HIERARCHY = {
    "admin": 100,
    "manager": 50,
    "user": 10,
    "guest": 0
}

class UserStub:
    """
    Replace this with your actual User model.
    """
    def __init__(self, obj_id: str, role: str):
        self.id = obj_id
        self.role = role

def _get_user_model(user_id: str = Depends(get_current_user)) -> UserStub:
    # TODO: Fetch actual user from DB: return await db.get(User, user_id)
    return UserStub(obj_id=user_id, role="user")

def require_role(min_role: str) -> Callable:
    """
    Dependency factory to lock endpoints by role.
    Checks the role hierarchy to allow higher roles.
    """
    min_role_weight = ROLE_HIERARCHY.get(min_role, 0)

    async def _role_checker(user: UserStub = Depends(_get_user_model)) -> UserStub:
        user_weight = ROLE_HIERARCHY.get(user.role, 0)
        
        if user_weight < min_role_weight:
            raise ForbiddenException(detail=f"Require '{min_role}' privileges")
            
        return user
        
    return _role_checker

def require_permissions(permissions: List[str]) -> Callable:
    """
    Dependency factory to lock endpoints by specific explicit permissions.
    """
    async def _permission_checker(user: UserStub = Depends(_get_user_model)) -> UserStub:
        # TODO: Implement granular permission lookup
        # e.g., user_permissions = await db.get_user_permissions(user.id)
        user_permissions = ["read:data"] 
        
        missing = [p for p in permissions if p not in user_permissions]
        if missing:
            raise ForbiddenException(detail=f"Missing permissions: {', '.join(missing)}")
            
        return user
        
    return _permission_checker
