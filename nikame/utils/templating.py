"""Jinja2 template engine for NIKAME.

All file generation (YAML, JSON, shell scripts, Dockerfiles, etc.)
MUST go through this module. Never use f-strings or string concatenation
to build structured output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from nikame.exceptions import NikameGenerationError
from nikame.utils.logger import get_logger

_log = get_logger("templating")

# Resolve the templates directory relative to the project root
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def _to_json_filter(value: Any, indent: int = 2) -> str:
    """Jinja2 filter: serialize a value to pretty JSON."""
    return json.dumps(value, indent=indent, sort_keys=True)


def _to_yaml_key(value: str) -> str:
    """Jinja2 filter: sanitize a string for use as a YAML key."""
    return value.replace(" ", "_").replace("-", "_").lower()


def create_jinja_env(templates_dir: Path | None = None) -> Environment:
    """Create a configured Jinja2 environment.

    Args:
        templates_dir: Path to templates directory. Defaults to
            the project's templates/ folder.

    Returns:
        Configured Jinja2 Environment.
    """
    tpl_dir = templates_dir or _TEMPLATES_DIR
    if not tpl_dir.exists():
        tpl_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,
    )
    env.filters["to_json"] = _to_json_filter
    env.filters["to_yaml_key"] = _to_yaml_key
    return env


def render_template(
    template_name: str,
    context: dict[str, Any],
    *,
    templates_dir: Path | None = None,
) -> str:
    """Render a Jinja2 template with the given context.

    Args:
        template_name: Relative path to template within templates dir.
        context: Template variables.
        templates_dir: Override templates directory.

    Returns:
        Rendered template string.

    Raises:
        NikameGenerationError: If template not found or rendering fails.
    """
    try:
        env = create_jinja_env(templates_dir)
        template = env.get_template(template_name)
        rendered = template.render(**context)
        _log.debug("Rendered template: %s", template_name)
        return rendered
    except Exception as exc:
        raise NikameGenerationError(
            f"Failed to render template '{template_name}': {exc}"
        ) from exc
