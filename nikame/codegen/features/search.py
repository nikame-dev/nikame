"""Search feature codegen for NIKAME.

Provides full-text search capabilities.
"""

from __future__ import annotations

import os

from nikame.codegen.base import BaseCodegen, register_codegen

@register_codegen
class SearchCodegen(BaseCodegen):
    """Generates search functionality code."""

    NAME = "search"
    DESCRIPTION = "Full-text search (Postgres/Elasticsearch)"
    DEPENDENCIES: list[str] = ["auth"]
    MODULE_DEPENDENCIES: list[str] = ["postgres"]

    def generate(self) -> list[tuple[str, str]]:
        files = []
        template_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "templates", "features", "search"
        )

        for template_name in ["search_engine.py.j2"]:
            path = os.path.join(template_dir, template_name)
            with open(path, "r") as f:
                content = f.read()
            
            target_path = f"services/api/search/{template_name.replace('.j2', '')}"
            files.append((target_path, content))

        return files
