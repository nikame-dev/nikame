from typing import Optional
import httpx
from jose import jwt
from fastapi import HTTPException, status
from app.core.settings import settings

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

async def get_google_user_info(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        # Swap code for token
        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        response = await client.post(GOOGLE_TOKEN_URL, data=data)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to authenticate with Google",
            )
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        # Get user info
        headers = {"Authorization": f"Bearer {access_token}"}
        user_info_resp = await client.get(GOOGLE_USERINFO_URL, headers=headers)
        if user_info_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to fetch user info from Google",
            )
            
        return user_info_resp.json()
