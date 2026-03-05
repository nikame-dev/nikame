"""BackgroundJobs feature codegen for NIKAME.

Provides Celery/Redis background worker support.
"""

from __future__ import annotations

import os

from nikame.codegen.base import BaseCodegen
from nikame.codegen.registry import register_codegen


@register_codegen
class JobsCodegen(BaseCodegen):
    """Generates celery worker and tasks code."""

    NAME = "background_jobs"
    DESCRIPTION = "Celery worker and Beat scheduler"
    DEPENDENCIES: list[str] = []
    MODULE_DEPENDENCIES: list[str] = ["redis"]

    def generate(self) -> list[tuple[str, str]]:
        files = []
        template_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "templates", "features", "background_jobs"
        )

        for template_name in ["celery_app.py.j2", "tasks.py.j2"]:
            path = os.path.join(template_dir, template_name)
            with open(path) as f:
                content = f.read()

            target_path = f"services/api/background_jobs/{template_name.replace('.j2', '')}"
            files.append((target_path, content))

        return files
