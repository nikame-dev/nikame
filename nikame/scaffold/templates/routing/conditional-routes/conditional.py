"""
Feature-flagged conditional routing.

This router should be mounted conditionally in main.py:

    from {{APP_NAME}}.core.settings import settings
    from {{APP_NAME}}.routers.conditional import router as experimental_router
    
    if getattr(settings, "ENABLE_EXPERIMENTAL_FEATURES", False):
        app.include_router(experimental_router)
"""
from fastapi import APIRouter

router = APIRouter(
    prefix="/experimental",
    tags=["Experimental Features"],
)

@router.get("/")
async def experimental_feature() -> dict[str, str]:
    return {"message": "This feature is enabled"}
