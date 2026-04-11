from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.jwt import create_access_token, get_current_user
from app.schemas.auth import TokenResponse, UserResponse
from app.core.error_handlers import UnauthorizedException

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """
    OAuth2 compatible token login, required for Swagger UI.
    In real usage, replace the hard-coded check with a DB lookup.
    """
    # TODO: Replace with real user lookup from DB using form_data.username
    if form_data.username != "admin" or form_data.password != "admin":
        raise UnauthorizedException(detail="Incorrect username or password")
    
    # Assume 1 is the user_id
    access_token = create_access_token(subject="1")
    return TokenResponse(access_token=access_token)

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user_id: str = Depends(get_current_user)) -> UserResponse:
    """
    Get current logged in user.
    """
    # TODO: Replace with real user lookup using current_user_id
    return UserResponse(id=current_user_id, username="admin", is_active=True)
