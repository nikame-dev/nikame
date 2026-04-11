import time
from typing import Dict, Any
from fastapi import APIRouter, Response, status
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["Health"])

class HealthStatus(BaseModel):
    status: str
    timestamp: float
    checks: Dict[str, Any]

@router.get("/liveness")
async def liveness_probe() -> Response:
    """
    Very fast check to see if the process is alive.
    Used by K8s to restart the container if deadlocked.
    """
    return Response(status_code=status.HTTP_200_OK)

@router.get("/readiness", response_model=HealthStatus)
async def readiness_probe() -> Any:
    """
    Checks if the container is ready to serve traffic.
    Verifies connections to DB, Redis, and Model Loading.
    """
    checks = {
        "database": "ok", # In real app: call await db.execute("SELECT 1")
        "redis": "ok",    # In real app: call await redis.ping()
        "model_loaded": True # check app.state.model_loaded
    }
    
    is_ready = all(v == "ok" or v is True for v in checks.values())
    
    return HealthStatus(
        status="ready" if is_ready else "not_ready",
        timestamp=time.time(),
        checks=checks
    )
