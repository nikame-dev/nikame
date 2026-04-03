"""Pydantic schemas for Auth."""
from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    is_superuser: bool = False

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_superuser: bool
    
    class Config:
        from_attributes = True
