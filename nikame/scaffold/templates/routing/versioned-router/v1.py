"""
API Version 1 Routes.

Marked as deprecated via OpenAPI configuration.
"""
from fastapi import APIRouter

router = APIRouter(
    prefix="/v1",
    tags=["v1 API (Deprecated)"],
    deprecated=True,  # This will show a strikethrough in Swagger UI
)

@router.get("/status")
async def get_status() -> dict[str, str]:
    return {"version": "v1", "status": "operational"}
