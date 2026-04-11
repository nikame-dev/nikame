import httpx
import json
from typing import Dict, Any, Optional
from urllib.parse import urlencode
from app.core.error_handlers import UnauthorizedException

GOOGLE_CLIENT_ID = "{{GOOGLE_CLIENT_ID}}"
GOOGLE_CLIENT_SECRET = "{{GOOGLE_CLIENT_SECRET}}"
OAUTH_CALLBACK_URL = "{{OAUTH_CALLBACK_URL}}"  # e.g. "http://localhost:8000/auth/oauth2/callback/google"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

def get_google_auth_url() -> str:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": OAUTH_CALLBACK_URL,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

async def exchange_code_for_google_user(code: str) -> Dict[str, Any]:
    """
    Exchanges the OAuth authorization code for an access token,
    then fetches the user's profile and returns Google's standard user structure.
    """
    token_data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": OAUTH_CALLBACK_URL,
    }
    
    async with httpx.AsyncClient() as client:
        token_res = await client.post(GOOGLE_TOKEN_URL, data=token_data)
        if token_res.status_code != 200:
            raise UnauthorizedException(detail="Failed to exchange authorization code for token")
            
        access_token = token_res.json().get("access_token")
        if not access_token:
            raise UnauthorizedException(detail="Access token not present in Google response")

        user_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if user_res.status_code != 200:
            raise UnauthorizedException(detail="Failed to fetch user info from Google")
            
        return user_res.json()

async def upsert_oauth_user(provider: str, provider_uid: str, email: str, name: Optional[str]) -> str:
    """
    Takes the OAuth2 info, registers or fetches the user in the database,
    and returns a standard internal system User ID.
    """
    # TODO: Perform lookup: e.g. "SELECT * FROM users WHERE email = $1"
    # If exists, return user.id. 
    # If not exists, insert user record, set email_verified=True, and return new user.id.
    
    dummy_internal_user_id = "oauth-user-999"
    return dummy_internal_user_id
