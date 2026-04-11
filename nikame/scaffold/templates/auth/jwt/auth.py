from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel
from fastapi import Request, Depends
from fastapi.security import OAuth2PasswordBearer
from app.core.error_handlers import UnauthorizedException

# These should ideally come from app.core.settings
SECRET_KEY = "{{SECRET_KEY}}" # e.g. "a-very-secret-key"
ALGORITHM = "{{ALGORITHM}}" # e.g. "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = {{ACCESS_TOKEN_EXPIRE_MINUTES}} # e.g. 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class TokenData(BaseModel):
    sub: str
    exp: datetime

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: str | Any, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dependency to get the current user from auth token.
    Replace return type `str` with your complete User model loaded from DB.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException(detail="Could not validate credentials")
        token_data = TokenData(sub=user_id, exp=datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc))
    except JWTError:
        raise UnauthorizedException(detail="Could not validate credentials")
    
    # Normally fetch user from DB here: user = await get_db().get_user(user_id)
    return token_data.sub
