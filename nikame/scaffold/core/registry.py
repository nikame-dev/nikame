import os
try:
    import tomli
except ImportError:
    import tomllib as tomli
from pathlib import Path
from typing import Dict, List, Optional, Any

class PatternMetadata:
    def __init__(self, slug: str, name: str, description: str, category: str, pattern_dir: Path = None):
        self.slug = slug
        self.name = name
        self.description = description
        self.category = category
        self.difficulty = "Beginner"
        self.tags = [category]
        self.depends_on = []
        self.template_vars = []  # FIX: Scaffolder expects this list
        self.files = []         # FIX: Scaffolder expects this list
        self.dependencies = []
        self.deps = []
        self.pattern_dir = pattern_dir

PatternMeta = PatternMetadata

class PatternFile:
    def __init__(self, src: str = "", dest: str = "", merge: str = "replace", path: str = "", content: str = ""):
        self.src = src
        self.dest = dest
        self.merge = merge
        self.path = path
        self.content = content

class PatternRegistry:
    def __init__(self, templates_dir: Optional[Path] = None):
        if templates_dir is None:
            self.templates_dir = Path("/home/omdeep-borkar/projects/nikame/nikame/scaffold/templates")
        else:
            self.templates_dir = templates_dir
        self.patterns: Dict[str, PatternMetadata] = {}

    def discover(self):
        if not self.templates_dir.exists(): return
        for cat_dir in self.templates_dir.iterdir():
            if cat_dir.is_dir():
                for p_dir in cat_dir.iterdir():
                    if p_dir.is_dir():
                        slug = f"{cat_dir.name}/{p_dir.name}"
                        meta = PatternMetadata(
                            slug=slug,
                            name=p_dir.name.replace("-", " ").title(),
                            description=f"Generated pattern for {slug}",
                            category=cat_dir.name,
                            pattern_dir=p_dir
                        )
                        # Scan for pattern.toml to load actual vars if present
                        toml_path = p_dir / "pattern.toml"
                        if toml_path.exists():
                            try:
                                mode = "rb"
                                with open(toml_path, mode) as f:
                                    data = tomli.load(f)
                                    meta.template_vars = data.get("template_vars", [])
                                    raw_files = data.get("files", [])
                                    meta.files = [PatternFile(**f) if isinstance(f, dict) else f for f in raw_files]
                                    meta.dependencies = data.get("depends_on", [])
                                    meta.deps = data.get("deps", [])
                            except: pass
                        self.patterns[slug] = meta

    def get(self, slug: str) -> Optional[PatternMetadata]:
        return self.get_pattern(slug)

    def get_pattern(self, slug: str) -> Optional[PatternMetadata]:
        if not self.patterns: self.discover()
        return self.patterns.get(slug)

    def all(self) -> List[PatternMetadata]:
        if not self.patterns: self.discover()
        return list(self.patterns.values())

    def resolve_dependencies(self, slug: str) -> List[str]:
        pattern = self.get(slug)
        if not pattern:
            return []
        return pattern.dependencies

    def by_category(self, category: str) -> List[PatternMetadata]:
        return [p for p in self.all() if p.category == category]

    def by_tag(self, tag: str) -> List[PatternMetadata]:
        return [p for p in self.all() if tag in p.tags]

    def search(self, query: str, threshold: int = 40) -> List[PatternMetadata]:
        query = query.lower()
        results = [p for p in self.all() if query in p.slug.lower() or query in p.name.lower() or query in p.description.lower()]
        return results


_registry = None
def get_registry():
    global _registry
    if _registry is None:
        _registry = PatternRegistry()
        _registry.discover()
    return _registry
