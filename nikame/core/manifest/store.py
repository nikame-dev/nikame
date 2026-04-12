from pathlib import Path

import yaml

try:
    from httpx import __version__ as httpx_version
except ImportError:
    httpx_version = "unknown"

from .migrator import migrate_manifest
from .schema import ManifestV2

# Actually it's better to fetch nikame version properly, but we'll hardcode 2.0 for now
NIKAME_VERSION = "2.0.0"

class ManifestStore:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.manifest_path = self.project_root / ".nikame" / "context.yaml"
    
    def load(self) -> ManifestV2 | None:
        if not self.manifest_path.exists():
            return None
        
        raw = yaml.safe_load(self.manifest_path.read_text())
        if not raw:
            return None
            
        version = str(raw.get("manifest_version", "1"))
        if version != "2":
            raw = migrate_manifest(raw, version)
            
        return ManifestV2(**raw)
        
    def save(self, manifest: ManifestV2) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        # Assuming Pydantic v2
        data = manifest.model_dump(mode="json")
        self.manifest_path.write_text(yaml.dump(data, sort_keys=False))
