\"\"\"Auth routing and logic.\"\"\"
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from core.database import get_db
from . import schemas, models, security
import logging

from core.messaging import kafka_service\n

logger = logging.getLogger(__name__)
router = APIRouter()
has_messaging = True

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
    await db.refresh(db_obj)
    if has_messaging:
        await kafka_service.send_message("user.events", {"event": "registered", "user_id": db_obj.id, "email": db_obj.email})
    return db_obj

@router.post("/login", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=60)
    token = security.create_access_token(user.id, expires_delta=access_token_expires)
    if has_messaging:
        await kafka_service.send_message("user.events", {"event": "logged_in", "user_id": user.id, "email": user.email})
    return {"access_token": token, "token_type": "bearer"}
