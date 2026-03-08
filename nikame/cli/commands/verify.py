"""nikame verify — Validate generated code health.

Checks for import consistency, requirements completion, and basic
FastAPI application health before 'nikame up'.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from nikame.utils.logger import console


@click.command()
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory to verify.",
)
def verify(project_dir: Path) -> None:
    """Verify that the generated code is runnable and has no missing imports."""
    with console.status("[info]Verifying generated code health...[/info]"):
        app_dir = project_dir / "app"
        if not app_dir.exists():
            console.print("[error]✗ Error: 'app/' directory not found. Is this a NIKAME project?[/error]")
            raise SystemExit(1)

        # 1. Check requirements.txt
        req_file = app_dir / "requirements.txt"
        if not req_file.exists():
            console.print("[error]✗ Error: app/requirements.txt not found.[/error]")
            raise SystemExit(1)
        console.print("[info]✓ requirements.txt exists[/info]")

        # 2. Check basic imports via a subprocess to avoid polluting current process
        # We need to add the app directory to PYTHONPATH
        env = {"PYTHONPATH": str(app_dir)}
        
        # Test app.main import
        try:
            subprocess.run(
                [sys.executable, "-c", "import main; print('Import successful')"],
                cwd=str(app_dir),
                env=env,
                check=True,
                capture_output=True,
                text=True
            )
            console.print("[info]✓ app/main.py is importable[/info]")
        except subprocess.CalledProcessError as e:
            console.print("[error]✗ Error: Failed to import app/main.py[/error]")
            console.print(f"[dim]{e.stderr}[/dim]")
            raise SystemExit(1)

        # 3. Verify all routers are importable
        router_dir = app_dir / "routers"
        if router_dir.exists():
            for router_file in router_dir.glob("*.py"):
                if router_file.name == "__init__.py":
                    continue
                module_name = f"routers.{router_file.stem}"
                try:
                    subprocess.run(
                        [sys.executable, "-c", f"import {module_name}"],
                        cwd=str(app_dir),
                        env=env,
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    console.print(f"[info]  ✓ {module_name} is importable[/info]")
                except subprocess.CalledProcessError as e:
                    console.print(f"[error]✗ Error: Failed to import {module_name}[/error]")
                    console.print(f"[dim]{e.stderr}[/dim]")
                    raise SystemExit(1)
            console.print("[info]✓ All router imports resolved[/info]")

        # 4. Final check: Can we instantiate the FastAPI app object?
        try:
            subprocess.run(
                [sys.executable, "-c", "from main import app; print(app.title)"],
                cwd=str(app_dir),
                env=env,
                check=True,
                capture_output=True,
                text=True
            )
            console.print("[success]✨ Verification complete: Generated code is healthy! ✨[/success]")
        except subprocess.CalledProcessError as e:
            console.print("[error]✗ Error: Failed to instantiate FastAPI application[/error]")
            console.print(f"[dim]{e.stderr}[/dim]")
            raise SystemExit(1)
