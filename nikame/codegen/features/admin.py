"""Admin feature codegen for NIKAME.

Provides SQLAdmin panel for easy database management.
"""

from __future__ import annotations

import os

from nikame.codegen.base import BaseCodegen
from nikame.codegen.registry import register_codegen


@register_codegen
class AdminCodegen(BaseCodegen):
    """Generates SQLAdmin dashboard code."""

    NAME = "admin_panel"
    DESCRIPTION = "SQLAdmin dashboard for models"
    DEPENDENCIES: list[str] = ["auth", "profiles"]
    MODULE_DEPENDENCIES: list[str] = ["postgres"]

    def generate(self) -> list[tuple[str, str]]:
        files = []
        template_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "templates", "features", "admin"
        )

        for template_name in ["admin_panel.py.j2"]:
            path = os.path.join(template_dir, template_name)
            with open(path) as f:
                content = f.read()

            target_path = f"services/api/admin/{template_name.replace('.j2', '')}"
            files.append((target_path, content))

        return files
