from pathlib import Path

import yaml

from .schema import PatternManifest


class RegistryLoader:
    def __init__(self, registry_dir: str | Path) -> None:
        self.registry_dir = Path(registry_dir)
        self._cache: dict[str, PatternManifest] = {}
        
    def load_all(self) -> list[PatternManifest]:
        patterns: list[PatternManifest] = []
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
                import logging
                logging.getLogger(__name__).warning(f"Failed to load {manifest_path}: {e}")
        return patterns
        
    def get_pattern(self, pattern_id: str) -> PatternManifest | None:
        if not self._cache:
            self.load_all()
        return self._cache.get(pattern_id)

    def load_pattern(self, pattern_id: str) -> PatternManifest | None:
        """Alias for get_pattern for CLI compatibility."""
        return self.get_pattern(pattern_id)
