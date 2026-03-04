"""Profiles feature codegen for NIKAME.

Provides user profile management and avatar upload.
"""

from __future__ import annotations

import os
from typing import Any

from nikame.codegen.base import BaseCodegen, CodegenContext
from nikame.codegen.registry import register_codegen


@register_codegen
class ProfilesCodegen(BaseCodegen):
    """Generates user profile management code."""

    NAME = "profiles"
    DESCRIPTION = "User profile creation and editing"
    DEPENDENCIES: list[str] = ["auth"]
    MODULE_DEPENDENCIES: list[str] = ["postgres"]

    def generate(self) -> list[tuple[str, str]]:
        """Render templates for the profiles feature."""
        files = []
        template_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "templates", "features", "profiles"
        )

        for template_name in [
            "models.py.j2",
            "schemas.py.j2",
            "router.py.j2",
        ]:
            path = os.path.join(template_dir, template_name)
            with open(path, "r") as f:
                content = f.read()
            
            target_path = f"services/api/profiles/{template_name.replace('.j2', '')}"
            files.append((target_path, content))

        return files
