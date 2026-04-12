from pathlib import Path

import yaml
from typing import Any
from rich.console import Console

from .migrator import migrate_config
from .schema import NikameConfig

console = Console()

class ConfigValidationError(Exception):
    pass


class ConfigLoader:
    """Loader for NIKAME project configuration (nikame.yaml)."""
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.config_path = project_root / "nikame.yaml"

    def load(self) -> NikameConfig | None:
        """Loads and validates the configuration from nikame.yaml."""
        if not self.config_path.exists():
            return None
            
        try:
            return load_config(self.config_path)
        except Exception:
            return None


def load_config(path: Path | str) -> NikameConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
        
    try:
        raw = yaml.safe_load(p.read_text())
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML format: {e}")
        
    version = str(raw.get("version", "1.0"))
    if version != "2.0":
        raw = migrate_config(raw, version)
        
    try:
        return NikameConfig(**raw)
    except Exception as e:
        console.print(f"[bold red]Configuration Validation Error:[/bold red] {e}")
        raise ConfigValidationError("Failed to validate config schema.") from e
