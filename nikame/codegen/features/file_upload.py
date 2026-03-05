"""FileUpload feature codegen for NIKAME.

Provides MinIO integration for file storage.
"""

from __future__ import annotations

import os

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
        files = []
        template_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "templates", "features", "file_upload"
        )

        for template_name in ["service.py.j2", "router.py.j2"]:
            path = os.path.join(template_dir, template_name)
            with open(path) as f:
                content = f.read()

            target_path = f"services/api/storage/{template_name.replace('.j2', '')}"
            files.append((target_path, content))

        return files
