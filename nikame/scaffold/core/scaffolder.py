"""
nikame scaffolder — the most critical component.

This is the intelligent file merge/copy engine that makes nikame
different from a folder of files. It handles:
  - Conflict detection with rich diffs
  - Smart merge for requirements.txt and __init__.py
  - Template variable substitution via Jinja2
  - Dependency chain resolution
  - Post-scaffold reporting
"""
from __future__ import annotations

import difflib
import re
import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment, BaseLoader
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from nikame.scaffold.core.config import get_config
from nikame.scaffold.core.registry import PatternMeta, PatternFile, get_registry

console = Console()


class ScaffoldResult:
    """Tracks what the scaffolder did for post-scaffold reporting."""

    def __init__(self, pattern: PatternMeta) -> None:
        self.pattern = pattern
        self.files_added: list[str] = []
        self.files_merged: list[str] = []
        self.files_skipped: list[str] = []
        self.deps_installed: list[str] = []
        self.env_vars_needed: list[str] = []
        self.imports_to_add: list[str] = []
        self.dependency_patterns: list[str] = []


class Scaffolder:
    """
    Intelligent file copy/merge engine.

    Never blindly overwrites. Always surgical.
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.registry = get_registry()
        self._jinja_env = Environment(
            loader=BaseLoader(),
            variable_start_string="{{",
            variable_end_string="}}",
            keep_trailing_newline=True,
        )

    def scaffold(
        self,
        slug: str,
        target_dir: Path,
        var_overrides: dict[str, str] | None = None,
        force: bool = False,
        dry_run: bool = False,
    ) -> ScaffoldResult | None:
        """
        Main entry point: scaffold a pattern into target_dir.

        1. Resolve dependency chain and scaffold deps first
        2. Copy/merge each file in the pattern manifest
        3. Merge requirements.txt
        4. Return a ScaffoldResult for reporting
        """
        pattern = self.registry.get(slug)
        if pattern is None:
            console.print(f"[red]✗[/red] Pattern '{slug}' not found.")
            return None

        result = ScaffoldResult(pattern)

        # Build template variable context
        template_vars = self._build_vars(pattern, var_overrides)

        # Resolve and scaffold dependencies first
        dep_slugs = self.registry.resolve_dependencies(slug)
        if dep_slugs:
            result.dependency_patterns = dep_slugs
            if not dry_run:
                for dep_slug in dep_slugs:
                    console.print(f"  [dim]→ Scaffolding dependency:[/dim] {dep_slug}")
                    self.scaffold(dep_slug, target_dir, var_overrides, force=force)

        # Scaffold each file in the pattern manifest
        for file_spec in pattern.files:
            self._scaffold_file(
                pattern=pattern,
                file_spec=file_spec,
                target_dir=target_dir,
                template_vars=template_vars,
                force=force,
                dry_run=dry_run,
                result=result,
            )

        # Merge requirements.txt
        self._merge_requirements(pattern, target_dir, dry_run, result)

        # Collect env vars needed
        result.env_vars_needed = list(pattern.template_vars)

        # Generate import suggestions
        result.imports_to_add = self._generate_import_suggestions(pattern, target_dir)

        return result

    def _build_vars(
        self,
        pattern: PatternMeta,
        overrides: dict[str, str] | None,
    ) -> dict[str, str]:
        """
        Build the complete template variable context.

        Priority: CLI overrides > config.toml template_vars > interactive prompt
        """
        vars_: dict[str, str] = {}
        config_vars = self.config.template_vars

        for var_name in pattern.template_vars:
            if overrides and var_name in overrides:
                vars_[var_name] = overrides[var_name]
            elif var_name in config_vars:
                vars_[var_name] = config_vars[var_name]
            else:
                # Interactive prompt for unresolved vars
                value = Prompt.ask(
                    f"  [cyan]Enter value for[/cyan] {var_name}",
                    default="",
                )
                vars_[var_name] = value

        # Always include APP_NAME and MODULE_NAME
        vars_.setdefault("APP_NAME", self.config.app_name)
        vars_.setdefault("MODULE_NAME", self.config.app_name)

        return vars_

    def _render_template(self, content: str, vars_: dict[str, str]) -> str:
        """Apply Jinja2 template variable substitution."""
        try:
            template = self._jinja_env.from_string(content)
            return template.render(**vars_)
        except Exception:
            # If templating fails, fall back to simple string substitution
            for key, value in vars_.items():
                content = content.replace(f"{{{{{key}}}}}", value)
            return content

    def _scaffold_file(
        self,
        pattern: PatternMeta,
        file_spec: PatternFile,
        target_dir: Path,
        template_vars: dict[str, str],
        force: bool,
        dry_run: bool,
        result: ScaffoldResult,
    ) -> None:
        """Process a single file from the pattern manifest."""
        src_path = pattern.pattern_dir / file_spec.src
        dest_path = target_dir / file_spec.dest

        if not src_path.exists():
            console.print(f"  [yellow]⚠[/yellow] Source file missing: {file_spec.src}")
            return

        # Read and render source content
        src_content = src_path.read_text()
        rendered_content = self._render_template(src_content, template_vars)

        if dry_run:
            status = "overwrite" if dest_path.exists() else "create"
            console.print(f"  [dim]{status}:[/dim] {file_spec.dest}")
            result.files_added.append(str(file_spec.dest))
            return

        if dest_path.exists() and not force:
            action = self._handle_conflict(
                dest_path, rendered_content, file_spec.merge
            )
            if action == "skip":
                result.files_skipped.append(str(file_spec.dest))
                return
            elif action == "merge":
                merged = self._merge_file(
                    dest_path.read_text(), rendered_content, file_spec.merge
                )
                dest_path.write_text(merged)
                result.files_merged.append(str(file_spec.dest))
                return
            elif action == "abort":
                console.print("[red]Aborted.[/red]")
                return
            # action == "overwrite" falls through to write

        # Write the file
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(rendered_content)
        result.files_added.append(str(file_spec.dest))

    def _handle_conflict(
        self, dest_path: Path, new_content: str, merge_strategy: str
    ) -> str:
        """Show a rich diff and prompt: Overwrite / Merge / Skip / Abort."""
        existing = dest_path.read_text()

        # Show diff
        diff = difflib.unified_diff(
            existing.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"existing: {dest_path.name}",
            tofile=f"incoming: {dest_path.name}",
        )
        diff_text = "".join(diff)

        if not diff_text:
            # Files are identical — skip silently
            return "skip"

        console.print(f"\n[yellow]⚠ Conflict:[/yellow] {dest_path}")
        console.print(Syntax(diff_text, "diff", theme="monokai", line_numbers=False))

        options = "[O]verwrite / [S]kip / [A]bort"
        if merge_strategy in ("append-exports", "merge-reqs"):
            options = "[O]verwrite / [M]erge / [S]kip / [A]bort"

        choice = Prompt.ask(f"  {options}", default="s").lower()

        return {
            "o": "overwrite",
            "m": "merge",
            "s": "skip",
            "a": "abort",
        }.get(choice, "skip")

    def _merge_file(
        self, existing: str, incoming: str, strategy: str
    ) -> str:
        """Merge two files based on the declared strategy."""
        if strategy == "append-exports":
            return self._merge_exports(existing, incoming)
        elif strategy == "merge-reqs":
            return self._merge_requirements_content(existing, incoming)
        else:
            return incoming  # default: replace

    def _merge_exports(self, existing: str, incoming: str) -> str:
        """
        Merge __init__.py exports: append new exports without duplicating.

        Looks for 'from .xxx import yyy' lines in incoming and adds
        only those not already present in existing.
        """
        existing_lines = set(existing.strip().splitlines())
        incoming_lines = incoming.strip().splitlines()

        new_lines = [line for line in incoming_lines if line not in existing_lines]

        if new_lines:
            merged = existing.rstrip() + "\n"
            merged += "\n# Added by nikame\n"
            merged += "\n".join(new_lines) + "\n"
            return merged

        return existing

    def _merge_requirements_content(self, existing: str, incoming: str) -> str:
        """Merge requirements.txt — append only missing packages."""
        existing_pkgs = self._parse_requirements(existing)
        incoming_pkgs = self._parse_requirements(incoming)
        incoming_lines = incoming.strip().splitlines()

        new_lines: list[str] = []
        for line in incoming_lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith("#"):
                continue
            pkg_name = self._extract_pkg_name(line_stripped)
            if pkg_name and pkg_name.lower() not in existing_pkgs:
                new_lines.append(line_stripped)

        if new_lines:
            merged = existing.rstrip() + "\n"
            merged += "\n".join(new_lines) + "\n"
            return merged

        return existing

    def _merge_requirements(
        self,
        pattern: PatternMeta,
        target_dir: Path,
        dry_run: bool,
        result: ScaffoldResult,
    ) -> None:
        """Merge pattern's deps into target project's requirements.txt."""
        if not pattern.deps:
            return

        req_path = target_dir / "requirements.txt"

        if dry_run:
            for dep in pattern.deps:
                console.print(f"  [dim]add dep:[/dim] {dep}")
            result.deps_installed = list(pattern.deps)
            return

        existing_pkgs: set[str] = set()
        existing_content = ""
        if req_path.exists():
            existing_content = req_path.read_text()
            existing_pkgs = self._parse_requirements(existing_content)

        new_deps: list[str] = []
        for dep in pattern.deps:
            pkg_name = self._extract_pkg_name(dep)
            if pkg_name and pkg_name.lower() not in existing_pkgs:
                new_deps.append(dep)

        if new_deps:
            content = existing_content.rstrip() + "\n" if existing_content else ""
            content += "\n".join(new_deps) + "\n"
            req_path.parent.mkdir(parents=True, exist_ok=True)
            req_path.write_text(content)
            result.deps_installed = new_deps

    def _parse_requirements(self, content: str) -> set[str]:
        """Extract normalised package names from requirements content."""
        pkgs: set[str] = set()
        for line in content.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            pkg_name = self._extract_pkg_name(line)
            if pkg_name:
                pkgs.add(pkg_name.lower())
        return pkgs

    @staticmethod
    def _extract_pkg_name(spec: str) -> str | None:
        """Extract package name from a pip specifier like 'foo[bar]>=1.0'."""
        match = re.match(r"^([a-zA-Z0-9_-]+)", spec.replace("[", " ").split()[0] if "[" in spec else spec)
        if match:
            name = re.split(r"[>=<!~]", match.group(1))[0]
            return name.strip()
        return None

    def _generate_import_suggestions(
        self, pattern: PatternMeta, target_dir: Path
    ) -> list[str]:
        """Generate import statements the engineer should add."""
        imports: list[str] = []
        app_name = self.config.app_name

        for file_spec in pattern.files:
            dest = file_spec.dest
            # Convert file path to import path
            # e.g. "auth/jwt.py" → "from app.auth.jwt import ..."
            module_path = dest.replace("/", ".").replace("\\", ".")
            if module_path.endswith(".py"):
                module_path = module_path[:-3]
            imports.append(f"from {app_name}.{module_path} import ...")

        return imports


def get_scaffolder() -> Scaffolder:
    return Scaffolder()
