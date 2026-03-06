"""Auth feature codegen for NIKAME.

Provides ASGI/FastAPI JWT-based authentication, user registration, and login.
"""

from __future__ import annotations
import logging
from nikame.codegen.base import BaseCodegen
from nikame.codegen.registry import register_codegen

@register_codegen
class AuthCodegen(BaseCodegen):
    """Generates deep-integrated Auth."""
    NAME = "auth"
    DESCRIPTION = "JWT authentication, registration, and login"
    DEPENDENCIES: list[str] = []
    MODULE_DEPENDENCIES: list[str] = ["postgres"]

    def generate(self) -> list[tuple[str, str]]:
        active_modules = self.ctx.active_modules
        has_messaging = any(m in ["redpanda", "kafka"] for m in active_modules)

        models_py = """\\"\\"\\"SQLAlchemy User Models.\\"\\"\\"
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
"""

        schemas_py = """\\"\\"\\"Pydantic schemas for Auth.\\"\\"\\"
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
"""

        security_py = """\\"\\"\\"Security utilities.\\"\\"\\"
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt

SECRET_KEY = "SUPER_SECRET_KEY_CHANGE_ME_IN_PROD"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(subject: str, expires_delta: timedelta):
    expire = datetime.utcnow() + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
"""

        kafka_import = "from core.messaging import kafka_service\\n" if has_messaging else ""
        kafka_publish_register = """
    if has_messaging:
        await kafka_service.send_message("user.events", {"event": "registered", "user_id": db_obj.id, "email": db_obj.email})""" if has_messaging else ""
        
        kafka_publish_login = """
    if has_messaging:
        await kafka_service.send_message("user.events", {"event": "logged_in", "user_id": user.id, "email": user.email})""" if has_messaging else ""

        router_py = f"""\\"\\"\\"Auth routing and logic.\\"\\"\\"
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from core.database import get_db
from . import schemas, models, security
import logging

{kafka_import}

logger = logging.getLogger(__name__)
router = APIRouter()
has_messaging = {'True' if has_messaging else 'False'}

@router.post("/register", response_model=schemas.UserResponse)
async def register(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    db_obj = models.User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        is_superuser=user_in.is_superuser
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj){kafka_publish_register}
    return db_obj

@router.post("/login", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=60)
    token = security.create_access_token(user.id, expires_delta=access_token_expires){kafka_publish_login}
    return {{"access_token": token, "token_type": "bearer"}}
"""
        return [
            ("app/api/auth/models.py", models_py),
            ("app/api/auth/schemas.py", schemas_py),
            ("app/api/auth/security.py", security_py),
            ("app/api/auth/router.py", router_py),
        ]
