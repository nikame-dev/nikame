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
    "--raw",
    is_flag=True,
    default=False,
    help="Show raw logs without JSON pretty-printing.",
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
    raw: bool,
    project_dir: Path,
) -> None:
    """Stream and pretty-print logs from running services."""
    import json
    import sys
    from rich.text import Text


    compose_file = project_dir / "infra" / "docker-compose.yml"
    if not compose_file.exists():
        console.print("[error]✗ docker-compose.yml not found. Run 'nikame init' first.[/error]")
        raise SystemExit(1)

    cmd = ["docker", "compose", "-f", str(compose_file)]
    env_file = project_dir / ".env.generated"
    if env_file.exists():
        cmd.extend(["--env-file", str(env_file)])
    
    # We use --no-log-prefix if not raw to make JSON parsing easier
    # But wait, standard docker compose logs output is: service-1 | {json}
    # We'll just split on ' | '
    

    cmd.extend(["logs", f"--tail={tail}"])
    if follow:
        cmd.append("-f")
    if service:
        cmd.extend(service)

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(project_dir)
        )

        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if not line:
                continue

            line = line.strip()
            if raw or " | " not in line:
                console.print(line)
                continue

            try:
                # Docker Compose format: "service_name | log_content"
                parts = line.split(" | ", 1)
                prefix = parts[0]
                content = parts[1]

                # Colorize prefix based on service name (simple hash)
                color = f"color({(hash(prefix) % 6) + 1})"
                prefix_text = Text(f"{prefix:15}", style=color)
                
                try:
                    data = json.loads(content)
                    # Pretty print JSON log
                    level = data.get("level", "INFO")
                    msg = data.get("message", content)
                    tm = data.get("timestamp", "")
                    
                    level_style = "bold red" if level in ["ERROR", "CRITICAL"] else "bold yellow" if level == "WARNING" else "bold blue"
                    
                    console.print(f"{prefix_text} | [dim]{tm}[/dim] [{level_style}]{level:7}[/{level_style}] {msg}")
                except (json.JSONDecodeError, TypeError):
                    console.print(f"{prefix_text} | {content}")
            except Exception:
                console.print(line)

    except subprocess.CalledProcessError:
        console.print("[error]✗ Failed to retrieve logs.[/error]")
        raise SystemExit(1)
    except KeyboardInterrupt:
        if 'process' in locals():
            process.terminate()
        pass
    finally:
        if 'process' in locals():
            process.wait()

