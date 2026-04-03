"""FileUpload feature codegen for NIKAME.

Provides MinIO integration for file storage.
"""

from __future__ import annotations
import logging
import os
import uuid
from nikame.codegen.base import BaseCodegen
from nikame.codegen.registry import register_codegen

@register_codegen
class FileUploadCodegen(BaseCodegen):
    """Generates file upload handling code."""

    NAME = "file_upload"
    DESCRIPTION = "MinIO/S3 file upload and presigned URLs"
    DEPENDENCIES: list[str] = ["auth"]
    MODULE_DEPENDENCIES: list[str] = ["minio"]

    def generate(self) -> list[tuple[str, str]]:
        active_modules = self.ctx.active_modules
        has_storage = any(m in ["minio", "s3"] for m in active_modules)

        router_py = '''"""File upload routing and logic."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from core.database import get_db
from core.storage import storage_client
import logging
import uuid
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])
BUCKET_NAME = "uploads"

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file directly to storage."""
    file_ext = os.path.splitext(file.filename)[1]
    object_name = f"{uuid.uuid4()}{file_ext}"

    # Save temporarily
    temp_path = f"/tmp/{object_name}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())

    try:
        await storage_client.upload_file(temp_path, BUCKET_NAME, object_name)
    except Exception as e:
        logger.error(f"Failed to upload {object_name}: {e}")
        raise HTTPException(status_code=500, detail="Storage upload failed")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {"filename": file.filename, "object_name": object_name}

@router.get("/download/{object_name}")
async def get_presigned_url(object_name: str):
    """Get a presigned URL for downloading a file."""
    try:
        url = await storage_client.generate_presigned_url(BUCKET_NAME, object_name)
        return {"url": url}
    except Exception as e:
        logger.error(f"Failed to generate URL for {object_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate URL")
'''

        return [
            ("app/api/storage/router.py", router_py),
        ]
