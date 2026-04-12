from pathlib import Path
import yaml
from typing import Dict, List
from .schema import PatternManifest

class RegistryLoader:
    def __init__(self, registry_dir: str | Path):
        self.registry_dir = Path(registry_dir)
        self._cache: Dict[str, PatternManifest] = {}
        
    def load_all(self) -> List[PatternManifest]:
        patterns = []
        if not self.registry_dir.exists():
            return patterns
            
        for manifest_path in self.registry_dir.rglob("manifest.yaml"):
            try:
                raw = yaml.safe_load(manifest_path.read_text())
                if raw and isinstance(raw, dict):
                    pattern = PatternManifest(**raw)
                    self._cache[pattern.id] = pattern
                    patterns.append(pattern)
            except Exception as e:
                # Log error or gracefully continue
                pass
        return patterns
        
    def get_pattern(self, pattern_id: str) -> PatternManifest | None:
        if not self._cache:
            self.load_all()
        return self._cache.get(pattern_id)
