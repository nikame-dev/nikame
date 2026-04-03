# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["Ops"])

@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    # 1. DB check
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except:
        pass

    # 2. Redis check (Optional)
    redis_ok = False
    try:
        r = redis.from_url("redis://redis:6379/0")
        await r.ping()
        redis_ok = True
    except:
        pass

    return {
        "status": "healthy" if db_ok and redis_ok else "unhealthy",
        "services": {
            "database": "up" if db_ok else "down",
            "cache": "up" if redis_ok else "down",
        }
    }