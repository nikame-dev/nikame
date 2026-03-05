"""Auth feature codegen for NIKAME.

Provides JWT-based authentication, user registration, and login.
"""

from __future__ import annotations

import os

from nikame.codegen.base import BaseCodegen
from nikame.codegen.registry import register_codegen


@register_codegen
class AuthCodegen(BaseCodegen):
    """Generates JWT authentication and user management code."""

    NAME = "auth"
    DESCRIPTION = "JWT authentication, registration, and login"
    DEPENDENCIES: list[str] = []
    MODULE_DEPENDENCIES: list[str] = ["postgres"]

    def generate(self) -> list[tuple[str, str]]:
        """Render templates for the auth feature."""
        files = []
        template_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "templates", "features", "auth"
        )

        # We'll use a simple file reading for now since we don't have a template engine helper yet
        # In a real scenario, we'd use Jinja2 to render with self.ctx
        for template_name in [
            "models.py.j2",
            "schemas.py.j2",
            "security.py.j2",
            "dependencies.py.j2",
            "router.py.j2",
        ]:
            path = os.path.join(template_dir, template_name)
            with open(path) as f:
                content = f.read()

            # Simple "rendering" — since these templates don't use variables yet
            # but they should in the future.
            target_path = f"services/api/auth/{template_name.replace('.j2', '')}"
            files.append((target_path, content))

        return files
