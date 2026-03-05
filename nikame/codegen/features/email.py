"""Email feature codegen for NIKAME.

Provides SMTP transactional email support.
"""

from __future__ import annotations

import os

from nikame.codegen.base import BaseCodegen
from nikame.codegen.registry import register_codegen


@register_codegen
class EmailCodegen(BaseCodegen):
    """Generates email sending logic."""

    NAME = "email"
    DESCRIPTION = "Transactional email (SMTP)"
    DEPENDENCIES: list[str] = []
    MODULE_DEPENDENCIES: list[str] = []

    def generate(self) -> list[tuple[str, str]]:
        files = []
        template_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "templates", "features", "email"
        )

        for template_name in ["service.py.j2"]:
            path = os.path.join(template_dir, template_name)
            with open(path) as f:
                content = f.read()

            target_path = f"services/api/email/{template_name.replace('.j2', '')}"
            files.append((target_path, content))

        return files
