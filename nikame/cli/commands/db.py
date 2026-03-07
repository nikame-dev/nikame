"""nikame db — Database migration management commands.

Wraps Alembic to provide `nikame db migrate`, `nikame db upgrade`,
`nikame db rollback`, and `nikame db history`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import click

from nikame.utils.logger import console


@click.group("db")
def db_group() -> None:
    """Database migration management (powered by Alembic)."""
    pass


@db_group.command()
@click.option("--message", "-m", required=True, help="Migration message.")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory.",
)
def migrate(message: str, project_dir: Path) -> None:
    """Generate a new migration from model changes (autogenerate)."""
    _ensure_alembic(project_dir)

    console.print(f"[info]Generating migration:[/info] {message}")
    try:
        subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", message],
            check=True,
            cwd=str(project_dir),
        )
        console.print("[success]✓ Migration created successfully.[/success]")
        console.print("[tip]Review the migration in alembic/versions/ before applying.[/tip]")
    except subprocess.CalledProcessError:
        console.print("[error]✗ Migration generation failed.[/error]")
        raise SystemExit(1)
    except FileNotFoundError:
        console.print("[error]✗ 'alembic' command not found. Install it: pip install alembic[/error]")
        raise SystemExit(1)


@db_group.command()
@click.option(
    "--revision", "-r", default="head", help="Target revision (default: head)."
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory.",
)
def upgrade(revision: str, project_dir: Path) -> None:
    """Apply migrations up to a target revision."""
    _ensure_alembic(project_dir)

    console.print(f"[info]Upgrading database to:[/info] {revision}")
    try:
        subprocess.run(
            ["alembic", "upgrade", revision],
            check=True,
            cwd=str(project_dir),
        )
        console.print("[success]✓ Database upgraded successfully.[/success]")
    except subprocess.CalledProcessError:
        console.print("[error]✗ Database upgrade failed.[/error]")
        raise SystemExit(1)
    except FileNotFoundError:
        console.print("[error]✗ 'alembic' command not found. Install it: pip install alembic[/error]")
        raise SystemExit(1)


@db_group.command()
@click.option(
    "--steps", "-n", default=1, help="Number of revisions to roll back (default: 1)."
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory.",
)
def rollback(steps: int, project_dir: Path) -> None:
    """Roll back the last N migrations."""
    _ensure_alembic(project_dir)

    target = f"-{steps}"
    console.print(f"[warning]Rolling back {steps} migration(s)...[/warning]")
    try:
        subprocess.run(
            ["alembic", "downgrade", target],
            check=True,
            cwd=str(project_dir),
        )
        console.print("[success]✓ Rollback complete.[/success]")
    except subprocess.CalledProcessError:
        console.print("[error]✗ Rollback failed.[/error]")
        raise SystemExit(1)
    except FileNotFoundError:
        console.print("[error]✗ 'alembic' command not found. Install it: pip install alembic[/error]")
        raise SystemExit(1)


@db_group.command()
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory.",
)
def history(project_dir: Path) -> None:
    """Show migration history."""
    _ensure_alembic(project_dir)

    try:
        subprocess.run(
            ["alembic", "history", "--verbose"],
            check=True,
            cwd=str(project_dir),
        )
    except subprocess.CalledProcessError:
        console.print("[error]✗ Could not retrieve migration history.[/error]")
        raise SystemExit(1)
    except FileNotFoundError:
        console.print("[error]✗ 'alembic' command not found. Install it: pip install alembic[/error]")
        raise SystemExit(1)


@db_group.command()
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory.",
)
def current(project_dir: Path) -> None:
    """Show current database revision."""
    _ensure_alembic(project_dir)

    try:
        subprocess.run(
            ["alembic", "current"],
            check=True,
            cwd=str(project_dir),
        )
    except subprocess.CalledProcessError:
        console.print("[error]✗ Could not retrieve current revision.[/error]")
        raise SystemExit(1)
    except FileNotFoundError:
        console.print("[error]✗ 'alembic' command not found. Install it: pip install alembic[/error]")
        raise SystemExit(1)


def _ensure_alembic(project_dir: Path) -> None:
    """Verify that alembic.ini exists in the project directory."""
    alembic_ini = project_dir / "alembic.ini"
    if not alembic_ini.exists():
        console.print("[error]✗ alembic.ini not found. Is Postgres enabled in this project?[/error]")
        console.print("[tip]Run 'nikame init' with Postgres to generate migration support.[/tip]")
        raise SystemExit(1)
