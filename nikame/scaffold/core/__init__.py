"""
nikame scaffold core — internal scaffolding engine.

Config is the single source of truth for template variables and general preferences.
Adapted from nikame for internal NIKAME use.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

import tomli_w


def _default_config_dir() -> Path:
    """Resolve NIKAME config directory from env or default."""
    return Path(os.environ.get("NIKAME_CONFIG_DIR", Path.home() / ".nikame"))


def _default_repo_dir() -> Path:
    """Resolve NIKAME scaffold internal registry directory."""
    # This file is in nikame/scaffold/core/__init__.py
    # We want nikame/scaffold/
    return Path(__file__).resolve().parent.parent


class NikameScaffoldConfig:
    """
    Loads and persists ~/.nikame/scaffold_config.toml.
    """

    def __init__(self, config_dir: Path | None = None, repo_dir: Path | None = None) -> None:
        self.config_dir = config_dir or _default_config_dir()
        self.repo_dir = repo_dir or _default_repo_dir()
        self.config_path = self.config_dir / "scaffold_config.toml"
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.config_path.exists():
            self._data = tomllib.loads(self.config_path.read_text())
        else:
            self._data = {}

    def save(self) -> None:
        """Persist current config back to disk."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_bytes(tomli_w.dumps(self._data).encode())

    def reload(self) -> None:
        self._load()

    @property
    def raw(self) -> dict[str, Any]:
        return self._data

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self._data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        if section not in self._data:
            self._data[section] = {}
        self._data[section][key] = value

    @property
    def app_name(self) -> str:
        return self.get("general", "app_name", "app")

    @property
    def template_vars(self) -> dict[str, str]:
        return dict(self._data.get("template_vars", {}))

    @property
    def templates_dir(self) -> Path:
        return self.repo_dir / "templates"

    @property
    def registry_path(self) -> Path:
        return self.repo_dir / "registry" / "registry.toml"


# Module-level singleton
_config: NikameScaffoldConfig | None = None


def get_config() -> NikameScaffoldConfig:
    global _config
    if _config is None:
        _config = NikameScaffoldConfig()
    return _config
