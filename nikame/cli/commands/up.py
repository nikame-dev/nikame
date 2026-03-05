"""nikame up — Start infrastructure services locally."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click

from nikame.utils.logger import console


@click.command()
@click.option(
    "--service", "-s",
    multiple=True,
    help="Specific service(s) to start. Omit for all.",
)
@click.option(
    "--build",
    is_flag=True,
    help="Rebuild images before starting.",
)
@click.option(
    "--detach/--no-detach", "-d",
    default=True,
    help="Run in detached mode (default: yes).",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory containing infra/.",
)
@click.pass_context
def up(
    ctx: click.Context,
    service: tuple[str, ...],
    build: bool,
    detach: bool,
    project_dir: Path,
) -> None:
    """Start NIKAME infrastructure services."""
    from nikame.config.loader import load_config
    config_path = project_dir / "nikame.yaml"

    if not config_path.exists():
        console.print("[error]✗ nikame.yaml not found.[/error]")
        raise SystemExit(1)

    config = load_config(config_path)
    target = config.environment.target

    if target == "local":
        _up_local(project_dir, service, build, detach)
    elif target in ["aws", "gcp", "azure"]:
        _up_cloud(project_dir, target)
    elif target == "kubernetes":
        _up_k8s(project_dir)
    else:
        console.print(f"[error]✗ Target '{target}' not yet supported for 'up'[/error]")

def _up_local(project_dir: Path, service: tuple[str, ...], build: bool, detach: bool) -> None:
    compose_file = project_dir / "infra" / "docker-compose.yml"
    if not compose_file.exists():
        console.print("[error]✗ docker-compose.yml not found. Run 'nikame init' first.[/error]")
        raise SystemExit(1)

    import questionary
    import yaml

    from nikame.utils.docker import find_conflicting_containers, stop_containers

    with open(compose_file) as f:
        try:
            compose_data = yaml.safe_load(f)
            conflicts = find_conflicting_containers(compose_data)
            if conflicts:
                console.print(f"[warning]⚠ Found {len(conflicts)} conflicting containers already running on host ports.[/warning]")
                for c in conflicts:
                    console.print(f"  - [key]{c.name}[/key] (image: {c.image.tags[0] if c.image.tags else 'unknown'})")
                
                if questionary.confirm("Would you like to stop these containers to proceed?").ask():
                    with console.status("[info]Stopping conflicting containers...[/info]"):
                        stop_containers(conflicts)
                    console.print("[success]✓ Conflicting containers stopped successfully.[/success]\n")
                else:
                    console.print("[error]✗ Port conflict detected. Aborting.[/error]")
                    raise SystemExit(1)
        except Exception as exc:
            console.print(f"[warning]⚠ Could not check for port conflicts: {exc}[/warning]")

    console.print("[success]🚀 Starting Local Services (Docker Compose)...[/success]\n")
    cmd = ["docker", "compose", "-f", str(compose_file)]
    env_file = project_dir / ".env.generated"
    if env_file.exists(): cmd.extend(["--env-file", str(env_file)])
    cmd.append("up")
    if detach: cmd.append("-d")
    if build: cmd.append("--build")
    if service: cmd.extend(service)

    # Validate volume paths before starting to avoid cryptic Docker errors
    volumes_to_check = [
        ("infra/configs/prometheus/prometheus.yml", "Prometheus config"),
        ("infra/configs/prometheus/alertmanager.yml", "Alertmanager config"),
        ("infra/configs/grafana/provisioning", "Grafana provisioning dir"),
    ]
    
    for rel_path, label in volumes_to_check:
        full_path = project_dir / rel_path
        if not full_path.exists():
            console.print(f"[warning]⚠ {label} missing at {rel_path}. Service may fail to start.[/warning]")

    try:
        subprocess.run(cmd, check=True, cwd=str(project_dir))
        
        # Priority 5: Health Check Verification
        _verify_health(config.name)
        
    except subprocess.CalledProcessError as e:
        console.print("\n[error]✗ Docker Compose failed to start services.[/error]")
        
        # Check for specific common Docker errors
        if "not a directory" in str(e) or "mount" in str(e).lower():
            console.print("\n[tip]💡 Potential Fix:[/tip]")
            console.print("This usually happens when Docker tries to mount a file that doesn't exist yet, ")
            console.print("and creates a directory instead. Try these steps:")
            console.print("1. [bold]rm -rf configs/[/bold] (if empty) or delete the offending directory.")
            console.print("2. Run [bold]nikame regenerate[/bold] to recreate missing config files.")
            console.print("3. Ensure you are on the latest version: [bold]pip install --upgrade nikame[/bold]")
        
        raise SystemExit(1)

def _verify_health(project_name: str) -> None:
    """Run health checks on all project containers and print status table."""
    from rich.table import Table
    from nikame.utils.docker import get_project_containers, get_container_logs
    import time
    
    with console.status("[info]Verifying service health... (waiting 5s for startup)[/info]"):
        time.sleep(5)
        containers = get_project_containers(project_name)
    
    if not containers:
        console.print("[warning]⚠ No containers found for this project.[/warning]")
        return

    table = Table(title=f"Service Status: {project_name}")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Health", style="bold")
    table.add_column("Endpoint/Port", style="green")

    unhealthy_containers = []

    for container in containers:
        name = container.name.split("-")[-2] if "-" in container.name else container.name
        status = container.status
        health = container.attrs.get("State", {}).get("Health", {}).get("Status", "N/A")
        
        # Color coding
        status_color = "green" if status == "running" else "red"
        health_color = "green" if health in ["healthy", "N/A"] else "yellow" if health == "starting" else "red"
        
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
            f"[{status_color}]{status}[/{status_color}]",
            f"[{health_color}]{health}[/{health_color}]",
            endpoint
        )

        if status != "running" or health == "unhealthy":
            unhealthy_containers.append(container)

    console.print("\n")
    console.print(table)
    
    if unhealthy_containers:
        console.print("\n[error]⚠ Some services are unhealthy or crashing:[/error]")
        for c in unhealthy_containers:
            console.print(f"\n[bold red]Logs for {c.name}:[/bold red]")
            logs = get_container_logs(c, tail=10)
            console.print(logs)
            console.print("-" * 40)
    else:
        console.print("\n[success]✨ All services are online and healthy![/success]")

def _up_k8s(project_dir: Path) -> None:
    k8s_dir = project_dir / "infra" / "kubernetes"
    helm_dir = project_dir / "infra" / "helm"

    if helm_dir.exists():
        console.print("[success]🚀 Deploying via Helm...[/success]\n")
        subprocess.run(["helm", "upgrade", "--install", "app", "."], check=True, cwd=str(helm_dir))
    elif k8s_dir.exists():
        console.print("[success]🚀 Deploying via Kubectl...[/success]\n")
        subprocess.run(["kubectl", "apply", "-f", "."], check=True, cwd=str(k8s_dir))
    else:
        console.print("[error]✗ No K8s or Helm files found.[/error]")

def _up_cloud(project_dir: Path, target: str) -> None:
    tf_dir = project_dir / "infra" / "terraform"
    if not tf_dir.exists():
        console.print("[error]✗ Terraform files not found.[/error]")
        raise SystemExit(1)

    console.print(f"[success]🚀 Provisioning Cloud Infrastructure ({target})...[/success]\n")
    subprocess.run(["terraform", "init"], check=True, cwd=str(tf_dir))
    subprocess.run(["terraform", "apply", "-auto-approve"], check=True, cwd=str(tf_dir))
