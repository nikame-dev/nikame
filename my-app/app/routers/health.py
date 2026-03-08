"""
Deep health checks for all system components.
"""

from fastapi import APIRouter, HTTPException
from config import settings
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["monitoring"])

@router.get("/")
async def liveness():
    """Basic liveness probe."""
    return {"status": "ok", "service": settings.APP_NAME}

@router.get("/ready")
async def readiness():
    """Deep readiness probe checking all sub-systems."""
    checks = {}
    
    # 1. Database
    if True:
        try:
            from core.database import engine
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "healthy"
        except Exception as e:
            logger.error(f"Health check: Database failed: {e}")
            checks["database"] = "unhealthy"

    # 2. Cache
    if True:
        try:
            from core.cache import cache
            await cache.ping()
            checks["cache"] = "healthy"
        except Exception as e:
            logger.error(f"Health check: Cache failed: {e}")
            checks["cache"] = "unhealthy"

    if "unhealthy" in checks.values():
        raise HTTPException(status_code=503, detail=checks)
        
    return {"status": "ready", "checks": checks}
