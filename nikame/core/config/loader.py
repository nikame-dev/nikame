import yaml
from pathlib import Path
from rich.console import Console

from .schema import NikameConfig
from .migrator import migrate_config

console = Console()

class ConfigValidationError(Exception):
    pass

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
