"""nikame logs — Stream service logs.

Thin wrapper around `docker compose logs` for convenience.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import click

from nikame.utils.logger import console


@click.command()
@click.option(
    "--service", "-s",
    multiple=True,
    help="Specific service(s) to show logs for.",
)
@click.option(
    "--follow", "-f",
    is_flag=True,
    default=False,
    help="Follow log output (like tail -f).",
)
@click.option(
    "--tail", "-n",
    default=100,
    help="Number of lines to show (default: 100).",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory.",
)
def logs(
    service: tuple[str, ...],
    follow: bool,
    tail: int,
    project_dir: Path,
) -> None:
    """Stream logs from running services."""
    compose_file = project_dir / "infra" / "docker-compose.yml"
    if not compose_file.exists():
        console.print("[error]✗ docker-compose.yml not found. Run 'nikame init' first.[/error]")
        raise SystemExit(1)

    cmd = ["docker", "compose", "-f", str(compose_file)]
    env_file = project_dir / ".env.generated"
    if env_file.exists():
        cmd.extend(["--env-file", str(env_file)])
    cmd.extend(["logs", f"--tail={tail}"])
    if follow:
        cmd.append("-f")
    if service:
        cmd.extend(service)

    try:
        subprocess.run(cmd, check=True, cwd=str(project_dir))
    except subprocess.CalledProcessError:
        console.print("[error]✗ Failed to retrieve logs.[/error]")
        raise SystemExit(1)
    except KeyboardInterrupt:
        pass
