"""YAML config loader with environment variable injection.

Parses nikame.yaml, resolves ${ENV_VAR} references, and produces
a validated NikameConfig instance.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from nikame.config.schema import NikameConfig
from nikame.exceptions import NikameValidationError
from nikame.utils.logger import get_logger

_log = get_logger("config.loader")

# Matches ${VAR_NAME} and ${VAR_NAME:-default}
_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}")


def _resolve_env_vars(value: str) -> str:
    """Replace ${VAR} and ${VAR:-default} in a string."""

    def _replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default = match.group(2)
        env_value = os.environ.get(var_name)
        if env_value is not None:
            return env_value
        if default is not None:
            return default
        # Keep the reference if not resolvable (will be in .env)
        return match.group(0)

    return _ENV_VAR_PATTERN.sub(_replacer, value)


def _walk_and_resolve(data: Any) -> Any:
    """Recursively resolve env vars in nested dicts/lists/strings."""
    if isinstance(data, str):
        return _resolve_env_vars(data)
    if isinstance(data, dict):
        return {k: _walk_and_resolve(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_walk_and_resolve(item) for item in data]
    return data


def load_config(
    config_path: Path,
    *,
    resolve_env: bool = True,
) -> NikameConfig:
    """Load and validate a nikame.yaml configuration file.

    Args:
        config_path: Path to nikame.yaml.
        resolve_env: Whether to resolve ${ENV_VAR} references.

    Returns:
        Validated NikameConfig instance.

    Raises:
        NikameValidationError: If file not found, YAML invalid, or
            schema validation fails.
    """
    if not config_path.exists():
        raise NikameValidationError(f"Config file not found: {config_path}")

    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise NikameValidationError(f"Cannot read config file: {exc}") from exc

    try:
        raw_data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise NikameValidationError(f"Invalid YAML in config file: {exc}") from exc

    if not isinstance(raw_data, dict):
        raise NikameValidationError(
            "Config file must be a YAML mapping (dict), got "
            f"{type(raw_data).__name__}"
        )

    if resolve_env:
        raw_data = _walk_and_resolve(raw_data)

    _log.debug("Loaded raw config with keys: %s", list(raw_data.keys()))

    # Flatten 'modules' group if present
    if "modules" in raw_data:
        modules_data = raw_data.pop("modules")
        if isinstance(modules_data, dict):
            for k, v in modules_data.items():
                if k not in raw_data or raw_data[k] is None:
                    raw_data[k] = v
        else:
            raise NikameValidationError("'modules' must be a dictionary")

    try:
        config = NikameConfig.model_validate(raw_data)
    except Exception as exc:
        raise NikameValidationError(
            f"Config validation failed: {exc}"
        ) from exc

    _log.debug("Config validated: project=%s, target=%s", config.name, config.environment.target)
    return config


def load_config_from_dict(data: dict[str, Any]) -> NikameConfig:
    """Validate a config dict directly (used by presets and tests).

    Args:
        data: Raw config dictionary.

    Returns:
        Validated NikameConfig instance.

    Raises:
        NikameValidationError: If validation fails.
    """
    try:
        return NikameConfig.model_validate(data)
    except Exception as exc:
        raise NikameValidationError(
            f"Config validation failed: {exc}"
        ) from exc
