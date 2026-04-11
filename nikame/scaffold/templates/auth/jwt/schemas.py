from typing import Optional
from pydantic import BaseModel, ConfigDict

class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    username: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    is_active: bool
