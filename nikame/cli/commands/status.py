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
        # Better name extraction: Docker Compose adds project_name-service_name-1
        # We want to extract just service_name
        raw_name = container.name
        project_prefix = f"{config.name}-"
        if raw_name.startswith(project_prefix):
            # Remove project prefix and trailing instance number (e.g. -1)
            name = raw_name[len(project_prefix):].rsplit("-", 1)[0]
        else:
            name = raw_name

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
    
    # ── ML-Specific Health Section ──
    _print_ml_health(containers, config.name)


def _print_ml_health(containers: list, project_name: str) -> None:
    """Show ML service health separately from infrastructure health."""
    from rich.table import Table
    import json
    
    ml_service_keywords = {
        "vllm", "ollama", "llamacpp", "tgi", "triton", "localai",
        "xinference", "airllm", "bentoml", "whisper", "tts",
        "mlflow", "langfuse", "evidently", "prefect",
    }
    
    ml_containers = []
    for c in containers:
        raw_name = c.name.lower()
        if any(kw in raw_name for kw in ml_service_keywords):
            ml_containers.append(c)

    if not ml_containers:
        return
    
    console.print("\n")
    table = Table(title=f"ML Service Health: {project_name}")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="magenta")
    
    for container in ml_containers:
        raw_name = container.name
        prefix = f"{project_name}-"
        name = raw_name[len(prefix):].rsplit("-", 1)[0] if raw_name.startswith(prefix) else raw_name
        
        state = container.status
        status_color = "green" if state == "running" else "red"
        
        # Attempt to fetch live telemetry per service type
        details = _get_ml_details(name, container)
        
        table.add_row(
            name,
            f"[{status_color}]{state}[/{status_color}]",
            details,
        )
    
    console.print(table)


def _get_ml_details(service_name: str, container) -> str:
    """Fetch model-specific runtime info from the live service."""
    try:
        import httpx
    except ImportError:
        return "—"
    
    # Resolve host port
    ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
    host_port = None
    for p, bindings in ports.items():
        if bindings:
            host_port = bindings[0].get("HostPort")
            break
    
    if not host_port:
        return "internal (no exposed port)"
    
    base = f"http://localhost:{host_port}"
    
    try:
        if "mlflow" in service_name:
            r = httpx.get(f"{base}/api/2.0/mlflow/experiments/search", timeout=3)
            if r.status_code == 200:
                exps = r.json().get("experiments", [])
                return f"{len(exps)} experiment(s) tracked"
        
        elif "langfuse" in service_name:
            r = httpx.get(f"{base}/api/public/health", timeout=3)
            if r.status_code == 200:
                return "Tracing active"
        
        elif "evidently" in service_name:
            r = httpx.get(f"{base}/api/projects", timeout=3)
            if r.status_code == 200:
                projects = r.json() if isinstance(r.json(), list) else []
                return f"{len(projects)} project(s) monitored"
        
        elif any(kw in service_name for kw in ("vllm", "tgi", "triton", "localai", "ollama")):
            # Try to hit a models endpoint
            r = httpx.get(f"{base}/v1/models", timeout=3)
            if r.status_code == 200:
                models = r.json().get("data", [])
                model_names = ", ".join(m.get("id", "?") for m in models[:3])
                return f"Models: {model_names}" if model_names else "Ready"
            # Fallback to health
            r = httpx.get(f"{base}/health", timeout=3)
            if r.status_code == 200:
                return "Healthy"
        
        elif "prefect" in service_name:
            return "Orchestrator active"
        
    except Exception:
        pass
    
    return "—"



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
