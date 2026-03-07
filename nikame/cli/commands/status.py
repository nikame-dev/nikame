"""nikame status — Show service status.

Displays the health and status of all running project containers.
"""

from __future__ import annotations

from pathlib import Path

import click

from nikame.utils.logger import console


@click.command()
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory.",
)
def status(project_dir: Path) -> None:
    """Show the status of all running services."""
    from rich.table import Table

    config_path = project_dir / "nikame.yaml"
    if not config_path.exists():
        console.print("[error]✗ nikame.yaml not found.[/error]")
        raise SystemExit(1)

    from nikame.config.loader import load_config
    config = load_config(config_path)

    try:
        from nikame.utils.docker import get_project_containers
    except Exception:
        console.print("[error]✗ Could not connect to Docker daemon.[/error]")
        raise SystemExit(1)

    containers = get_project_containers(config.name)

    if not containers:
        console.print(f"[warning]No running containers found for project '{config.name}'.[/warning]")
        console.print("[tip]Run 'nikame up' to start services.[/tip]")
        return

    table = Table(title=f"Service Status: {config.name}")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Health", style="bold")
    table.add_column("Uptime", style="dim")
    table.add_column("Endpoint", style="green")

    for container in containers:
        name = container.name.split("-")[-2] if "-" in container.name else container.name
        state = container.status
        health = container.attrs.get("State", {}).get("Health", {}).get("Status", "N/A")

        # Uptime
        started_at = container.attrs.get("State", {}).get("StartedAt", "")
        uptime = _format_uptime(started_at)

        # Color coding
        status_color = "green" if state == "running" else "red"
        health_color = "green" if health in ("healthy", "N/A") else "yellow" if health == "starting" else "red"

        # Get ports
        ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
        port_info = []
        for p, bindings in ports.items():
            if bindings:
                host_port = bindings[0].get("HostPort")
                port_info.append(f"localhost:{host_port}")
        endpoint = ", ".join(port_info) if port_info else "internal"

        table.add_row(
            name,
            f"[{status_color}]{state}[/{status_color}]",
            f"[{health_color}]{health}[/{health_color}]",
            uptime,
            endpoint,
        )

    console.print(table)


def _format_uptime(started_at: str) -> str:
    """Format Docker started_at timestamp into a human-readable uptime."""
    if not started_at:
        return "unknown"
    try:
        from datetime import datetime, timezone
        # Docker uses ISO 8601 with nanoseconds
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00").split(".")[0] + "+00:00")
        delta = datetime.now(timezone.utc) - started
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            return f"{total_seconds // 60}m {total_seconds % 60}s"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            return f"{days}d {hours}h"
    except Exception:
        return "unknown"
