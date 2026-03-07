"""Project Guide Generator for NIKAME.

Aggregates metadata from active modules and features to produce a
customized GUIDE.md for the generated project.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader

if TYPE_CHECKING:
    from nikame.blueprint.engine import Blueprint


class GuideGenerator:
    """Generates project-specific documentation."""

    def __init__(self, blueprint: Blueprint) -> None:
        self.blueprint = blueprint
        # Setup Jinja2
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "guide")
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def generate(self) -> str:
        """Render the GUIDE.md content."""
        metadata = self._collect_metadata()
        metadata["now"] = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            tmpl = self.env.get_template("GUIDE.md.j2")
            return tmpl.render(**metadata)
        except Exception as e:
            from nikame.utils.logger import console
            console.print(f"[warning]⚠ Template error in GUIDE.md: {e}[/warning]")
            return f"# {self.blueprint.project_name}\n\nProject generated with NIKAME."

    def _collect_metadata(self) -> dict[str, Any]:
        """Aggregate metadata from all components."""
        data = {
            "project_name": self.blueprint.project_name,
            "environment": self.blueprint.config.environment.target if self.blueprint.config else "local",
            "overviews": [],
            "urls": [],
            "api_examples": [],
            "feature_guides": [],
            "integrations": [],
            "troubleshooting": [],
            "active_modules": [m.NAME for m in self.blueprint.modules],
            "active_features": self.blueprint.features,
            "commands": self._get_global_commands(),
        }

        # 1. Collect from Modules
        for mod in self.blueprint.modules:
            meta = mod.guide_metadata()
            if meta.get("overview"):
                data["overviews"].append({"name": mod.NAME, "text": meta["overview"]})
            data["urls"].extend(meta.get("urls", []))
            data["integrations"].extend(meta.get("integrations", []))
            data["troubleshooting"].extend(meta.get("troubleshooting", []))

        # 2. Collect from Features
        from nikame.codegen.registry import get_codegen_class, discover_codegen
        from nikame.codegen.base import CodegenContext
        discover_codegen()
        
        ctx = CodegenContext(
            project_name=self.blueprint.project_name,
            active_modules=[m.NAME for m in self.blueprint.modules],
            features=self.blueprint.features
        )

        for feature in self.blueprint.features:
            cls = get_codegen_class(feature)
            if cls:
                gen = cls(ctx, self.blueprint.config)
                meta = gen.guide_metadata()
                data["api_examples"].extend(meta.get("api_examples", []))
                data["feature_guides"].extend(meta.get("feature_guides", []))

        return data

    def _get_global_commands(self) -> list[dict[str, str]]:
        """Return global nikame commands."""
        return [
            {"cmd": "nikame up", "desc": "Start the development environment"},
            {"cmd": "nikame stop", "desc": "Stop all services"},
            {"cmd": "nikame logs -f", "desc": "Follow logs of all services"},
            {"cmd": "nikame ps", "desc": "Check status of services"},
        ]
