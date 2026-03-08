"""Legacy wiring manager for NIKAME.

Handles safe injection of code (imports, routers, requirements) into 
an existing application scaffold using markers. 
Operates directly on the filesystem.
"""

from __future__ import annotations

from pathlib import Path

from nikame.codegen.base import WiringInfo


class WiringManager:
    """Manages injection and removal of feature wiring code."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.main_py = project_dir / "services/api/main.py"
        self.requirements_txt = project_dir / "services/api/requirements.txt"

    def apply(self, wiring_info: WiringInfo) -> None:
        """Apply wiring info to the project."""
        if self.main_py.exists():
            self._inject_into_main(wiring_info)

        if self.requirements_txt.exists():
            self._update_requirements(wiring_info.requirements)

    def remove(self, wiring_info: WiringInfo) -> None:
        """Remove wiring info from the project."""
        if self.main_py.exists():
            self._remove_from_main(wiring_info)

    def _inject_into_main(self, wiring_info: WiringInfo) -> None:
        """Inject imports and routers into main.py."""
        content = self.main_py.read_text()

        # 1. Inject Imports
        if wiring_info.imports:
            import_block = "\n".join(wiring_info.imports) + "\n"
            if "# NIKAME IMPORTS" in content:
                content = content.replace("# NIKAME IMPORTS", f"# NIKAME IMPORTS\n{import_block}")
            else:
                # Fallback: find last import
                lines = content.splitlines()
                last_import_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith("import ") or line.startswith("from "):
                        last_import_idx = i
                lines.insert(last_import_idx + 1, import_block)
                content = "\n".join(lines)

        # 2. Inject Routers
        if wiring_info.routers:
            router_block = "\n".join(wiring_info.routers) + "\n"
            if "# NIKAME ROUTERS" in content:
                content = content.replace("# NIKAME ROUTERS", f"# NIKAME ROUTERS\n{router_block}")
            else:
                # Fallback: append before root
                content = content.replace("@app.get(\"/\")", f"{router_block}\n@app.get(\"/\")")

        self.main_py.write_text(content)

    def _remove_from_main(self, wiring_info: WiringInfo) -> None:
        """Remove previously injected strings from main.py."""
        content = self.main_py.read_text()

        for imp in wiring_info.imports:
            content = content.replace(f"{imp}\n", "")

        for router in wiring_info.routers:
            content = content.replace(f"{router}\n", "")

        self.main_py.write_text(content)

    def _update_requirements(self, requirements: list[str]) -> None:
        """Add new requirements if not already present."""
        if not requirements:
            return

        content = self.requirements_txt.read_text()
        existing = {line.split(">=")[0].split("==")[0].strip().lower() for line in content.splitlines() if line.strip()}

        new_lines = []
        for req in requirements:
            name = req.split(">=")[0].split("==")[0].strip().lower()
            if name not in existing:
                new_lines.append(req)

        if new_lines:
            content += "\n" + "\n".join(new_lines) + "\n"
            self.requirements_txt.write_text(content)
