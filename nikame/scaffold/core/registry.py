"""
nikame scaffold registry — pattern discovery and metadata loading.

Scans nikame/scaffold/templates/ directory and loads pattern.toml files.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

from thefuzz import fuzz

from nikame.scaffold.core.config import get_config


@dataclass
class PatternFile:
    """A single file mapping in a pattern's manifest."""
    src: str
    dest: str
    merge: str = "replace"  # replace | append-exports | merge-reqs


@dataclass
class PatternMeta:
    """Full metadata for a single pattern, loaded from pattern.toml."""
    name: str
    slug: str
    category: str
    tags: list[str] = field(default_factory=list)
    description: str = ""
    difficulty: str = "beginner"  # beginner | intermediate | advanced
    deps: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    files: list[PatternFile] = field(default_factory=list)
    template_vars: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    pattern_dir: Path = field(default_factory=lambda: Path("."))

    @classmethod
    def from_toml(cls, path: Path) -> PatternMeta:
        """Parse a pattern.toml file into a PatternMeta instance."""
        raw: dict[str, Any] = tomllib.loads(path.read_text())
        files = [
            PatternFile(
                src=f["src"],
                dest=f["dest"],
                merge=f.get("merge", "replace"),
            )
            for f in raw.get("files", [])
        ]
        return cls(
            name=raw.get("name", path.parent.name),
            slug=raw.get("slug", ""),
            category=raw.get("category", ""),
            tags=raw.get("tags", []),
            description=raw.get("description", ""),
            difficulty=raw.get("difficulty", "beginner"),
            deps=raw.get("deps", []),
            depends_on=raw.get("depends_on", []),
            files=files,
            template_vars=raw.get("template_vars", []),
            related=raw.get("related", []),
            pattern_dir=path.parent,
        )

    @property
    def has_main(self) -> bool:
        """Whether this pattern has a standalone runnable main.py."""
        return (self.pattern_dir / "main.py").exists()

    @property
    def readme_path(self) -> Path:
        return self.pattern_dir / "README.md"

    @property
    def requirements_path(self) -> Path:
        return self.pattern_dir / "requirements.txt"


class PatternRegistry:
    """
    Discovers and indexes all patterns under internal templates/.
    """

    def __init__(self) -> None:
        self._patterns: dict[str, PatternMeta] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.scan()

    def scan(self) -> None:
        """Walk the internal templates directory and load every pattern.toml."""
        cfg = get_config()
        templates_dir = cfg.templates_dir
        self._patterns.clear()

        if not templates_dir.exists():
            self._loaded = True
            return

        for category_dir in sorted(templates_dir.iterdir()):
            if not category_dir.is_dir():
                continue
            for pattern_dir in sorted(category_dir.iterdir()):
                if not pattern_dir.is_dir():
                    continue
                toml_path = pattern_dir / "pattern.toml"
                if toml_path.exists():
                    try:
                        meta = PatternMeta.from_toml(toml_path)
                        if not meta.slug:
                            meta.slug = f"{category_dir.name}/{pattern_dir.name}"
                        self._patterns[meta.slug] = meta
                    except Exception as exc:
                        import sys
                        print(f"[warn] Failed to load {toml_path}: {exc}", file=sys.stderr)

        self._loaded = True

    def get(self, slug: str) -> PatternMeta | None:
        self._ensure_loaded()
        return self._patterns.get(slug)

    def all(self) -> list[PatternMeta]:
        self._ensure_loaded()
        return sorted(self._patterns.values(), key=lambda p: (p.category, p.slug))

    def by_category(self, category: str) -> list[PatternMeta]:
        self._ensure_loaded()
        return [p for p in self._patterns.values() if p.category == category]

    def by_tag(self, tag: str) -> list[PatternMeta]:
        self._ensure_loaded()
        return [p for p in self._patterns.values() if tag in p.tags]

    def categories(self) -> list[str]:
        self._ensure_loaded()
        return sorted({p.category for p in self._patterns.values()})

    def search(self, query: str, threshold: int = 50) -> list[PatternMeta]:
        self._ensure_loaded()
        results: list[tuple[int, PatternMeta]] = []

        for pattern in self._patterns.values():
            corpus = " ".join([
                pattern.name,
                pattern.slug,
                pattern.description,
                " ".join(pattern.tags),
            ])
            score = fuzz.partial_ratio(query.lower(), corpus.lower())
            if score >= threshold:
                results.append((score, pattern))

        results.sort(key=lambda r: r[0], reverse=True)
        return [p for _, p in results]

    def resolve_dependencies(self, slug: str, resolved: list[str] | None = None) -> list[str]:
        self._ensure_loaded()
        if resolved is None:
            resolved = []

        pattern = self.get(slug)
        if pattern is None:
            return resolved

        for dep_slug in pattern.depends_on:
            if dep_slug not in resolved:
                self.resolve_dependencies(dep_slug, resolved)
                resolved.append(dep_slug)

        return resolved


_registry: PatternRegistry | None = None


def get_registry() -> PatternRegistry:
    global _registry
    if _registry is None:
        _registry = PatternRegistry()
    return _registry
