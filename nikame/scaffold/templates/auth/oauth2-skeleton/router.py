from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from app.auth.oauth2 import get_google_auth_url, exchange_code_for_google_user, upsert_oauth_user
from app.auth.jwt import create_access_token

router = APIRouter(prefix="/auth/oauth2", tags=["OAuth2"])

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.get("/login/google", response_class=RedirectResponse)
async def login_via_google():
    """
    Redirects the user to the Google Consent screen.
    """
    url = get_google_auth_url()
    return RedirectResponse(url)

@router.get("/callback/google", response_model=TokenResponse)
async def callback_from_google(code: str = Query(...)):
    """
    Google redirects back to here. We exchange the code for the user profile,
    upsert the user in our DB, and generate our own system JWT.
    """
    google_user = await exchange_code_for_google_user(code)
    
    # google_user looks roughly like: {"id": "...", "email": "...", "name": "..."}
    internal_user_id = await upsert_oauth_user(
        provider="google",
        provider_uid=google_user.get("id", ""),
        email=google_user.get("email", ""),
        name=google_user.get("name", "")
    )
    
    # Proceed to authenticate exactly like regular JWT auth
    access_token = create_access_token(subject=internal_user_id)
    return TokenResponse(access_token=access_token)
