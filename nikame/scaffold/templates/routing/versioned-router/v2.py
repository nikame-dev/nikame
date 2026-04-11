"""
API Version 2 Routes.

The current active version.
"""
from fastapi import APIRouter

router = APIRouter(
    prefix="/v2",
    tags=["v2 API"],
)

@router.get("/status")
async def get_status() -> dict[str, str]:
    return {"version": "v2", "status": "operational", "new_feature": True}
