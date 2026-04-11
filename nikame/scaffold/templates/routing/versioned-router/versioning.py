"""
Versioned routers.

Exports the main API router that mounts v1 and v2 sub-routers.
"""
from fastapi import APIRouter

from {{APP_NAME}}.routers.v1 import router as v1_router
from {{APP_NAME}}.routers.v2 import router as v2_router

# Main API router
api_router = APIRouter(prefix="/api")

# Mount versioned sub-routers
api_router.include_router(v1_router)
api_router.include_router(v2_router)
