"""nikame up — Start infrastructure services locally."""

import shutil
import subprocess
from pathlib import Path
import time

import click

from nikame.utils.logger import console
from nikame.blueprint.engine import build_blueprint
from nikame.config.schema import NikameConfig


def _ensure_binary(name: str, install_hint: str) -> None:
    """Check if a binary exists in PATH, else raise helpful error."""
    if not shutil.which(name):
        console.print(f"\n[error]✗ Required tool [bold]'{name}'[/bold] not found in PATH.[/error]")
        console.print(f"[tip]💡 Install Hint:[/tip] {install_hint}")
        console.print("\n[cyan]Alternatives:[/cyan]")
        console.print("If you don't have Kubernetes installed, change [bold]target: local[/bold] in [bold]nikame.yaml[/bold] to use Docker Compose.")
        raise SystemExit(1)


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
        _up_local(project_dir, config, service, build, detach)
    elif target in ["aws", "gcp", "azure"]:
        _up_cloud(project_dir, target)
    elif target == "kubernetes":
        _up_k8s(project_dir)
    else:
        console.print(f"[error]✗ Target '{target}' not yet supported for 'up'[/error]")

def _up_local(project_dir: Path, config: NikameConfig, service: tuple[str, ...], build: bool, detach: bool) -> None:
    _ensure_binary("docker", "Visit https://docs.docker.com/get-docker/")
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

    # ── Pre-flight checks ──
    from nikame.cli.commands.preflight import (
        check_python_imports, check_env_vars, check_dockerfiles
    )
    critical_checks = [check_python_imports, check_env_vars, check_dockerfiles]
    preflight_failed = False
    for check_fn in critical_checks:
        try:
            result = check_fn(project_dir)
            if not result.passed and result.severity == "P0":
                console.print(f"  [red]✗ {result.name}:[/red] {result.message}")
                if result.fix_hint:
                    console.print(f"    [dim]Fix: {result.fix_hint}[/dim]")
                preflight_failed = True
            elif not result.passed:
                console.print(f"  [yellow]⚠ {result.name}:[/yellow] {result.message}")
        except Exception:
            pass
    if preflight_failed:
        console.print("\n[bold red]✗ Pre-flight failed. Fix P0 issues first.[/bold red]")
        raise SystemExit(1)

    cmd_base = ["docker", "compose", "-p", config.name, "-f", str(compose_file)]
    env_file = project_dir / ".env.generated"
    if env_file.exists(): cmd_base.extend(["--env-file", str(env_file)])

    # ── ML-Aware Dependency Ordering ──
    # Phase 1: Data stores (Postgres, Dragonfly/Redis, MinIO, Vector DBs)
    # Phase 2: ML Tracking & Observability (MLflow, LangFuse, Evidently, Prefect)
    # Phase 3: LLM Serving Engines (vLLM, TGI, Triton, etc.)
    #
    # If specific services are requested, skip ordering.
    if not service:
        all_services = list(compose_data.get("services", {}).keys())
        
        phase1_keywords = {"postgres", "pgbouncer", "dragonfly", "redis", "minio", "qdrant", "weaviate", "milvus", "chroma", "redpanda", "kafka", "clickhouse", "mongodb", "neo4j"}
        phase2_keywords = {"mlflow", "langfuse", "evidently", "prefect", "airflow", "grafana", "prometheus", "alertmanager"}
        phase3_keywords = {"vllm", "ollama", "llamacpp", "tgi", "triton", "localai", "xinference", "airllm", "bentoml", "whisper", "tts"}
        
        phase1 = [s for s in all_services if any(k in s for k in phase1_keywords)]
        phase2 = [s for s in all_services if any(k in s for k in phase2_keywords) and s not in phase1]
        phase3 = [s for s in all_services if any(k in s for k in phase3_keywords) and s not in phase1 and s not in phase2]
        remaining = [s for s in all_services if s not in phase1 and s not in phase2 and s not in phase3]
        
        phases = [
            ("Phase 1: Data Stores & Messaging", phase1),
            ("Phase 2: ML Tracking & Observability", phase2),
            ("Phase 3: Application & API", remaining),
            ("Phase 4: LLM Serving Engines", phase3),
        ]
        
        for label, svcs in phases:
            if svcs:
                console.print(f"  [info]{label}:[/info] {', '.join(svcs)}")
                phase_cmd = cmd_base + ["up", "-d"] + svcs
                try:
                    subprocess.run(phase_cmd, check=True, cwd=str(project_dir))  # noqa: S603
                    time.sleep(2)  # Brief pause between phases
                except subprocess.CalledProcessError:
                    console.print(f"\n[error]✗ Phase failed: {label}[/error]")
                    # Try to capture logs of failed containers in this phase
                    from nikame.utils.docker import get_project_containers, get_container_logs
                    containers = get_project_containers(config.name)
                    for c in containers:
                        svc_name = c.name.split("-")[-2] if "-" in c.name else c.name
                        if svc_name in svcs and (c.status != "running" or c.attrs.get("State", {}).get("Health", {}).get("Status") == "unhealthy"):
                            console.print(f"\n[bold red]Logs for {c.name}:[/bold red]")
                            console.print(get_container_logs(c, tail=20))
                    raise SystemExit(1)
        
    else:
        cmd = cmd_base + ["up"]
        if detach: cmd.append("-d")
        if build: cmd.append("--build")
        cmd.extend(service)
        subprocess.run(cmd, check=True, cwd=str(project_dir))  # noqa: S603

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
        
        # Priority 6: ML-Specific Service URLs
        _print_ml_urls(compose_data)
        
        # Priority 7: Display Ngrok Tunnel (if active)
        blueprint = build_blueprint(config)
        if "ngrok" in [m.NAME for m in blueprint.modules]:
            _display_ngrok_tunnel()
        
    except subprocess.CalledProcessError as e:
        console.print("\n[error]✗ Docker Compose failed to start services.[/error]")
        
        # Check for specific common Docker errors
        error_msg = str(e) or ""
        if "nvidia" in error_msg.lower() or "device driver" in error_msg.lower():
            console.print("\n[tip]💡 Hardware Error Detected (GPU):[/tip]")
            console.print("Docker could not find the 'nvidia' device driver. This usually means:")
            console.print("1. You don't have an NVIDIA GPU or the drivers are not installed.")
            console.print("2. The [bold]nvidia-container-toolkit[/bold] is not installed.")
            console.print("\n[cyan]To fix this (CPU Fallback):[/cyan]")
            console.print("Edit [bold]nikame.yaml[/bold] and set [bold]gpu: false[/bold] for your ML modules.")
            console.print("Then run [bold]nikame regenerate[/bold] and try again.")
        elif "not a directory" in error_msg or "mount" in error_msg.lower():
            console.print("\n[tip]💡 Potential Fix (Mount Error):[/tip]")
            console.print("This usually happens when Docker tries to mount a file that doesn't exist yet, ")
            console.print("and creates a directory instead. Try these steps:")
            console.print("1. [bold]rm -rf configs/[/bold] (if empty) or delete the offending directory.")
            console.print("2. Run [bold]nikame regenerate[/bold] to recreate missing config files.")
            console.print("3. Ensure you are on the latest version: [bold]pip install --upgrade nikame[/bold]")
        
        raise SystemExit(1)

def _print_ml_urls(compose_data: dict) -> None:
    """Print ML-specific UI URLs if those services exist."""
    from rich.table import Table
    
    ml_urls = {
        "mlflow": ("MLflow Tracking UI", 5000),
        "langfuse": ("LangFuse Tracing UI", 3000),
        "prefect-server": ("Prefect Orchestration UI", 4200),
        "airflow-webserver": ("Airflow DAG UI", 8080),
        "evidently": ("Evidently AI Dashboard", 8000),
        "grafana": ("Grafana Dashboards", 3001),
    }
    
    services = compose_data.get("services", {})
    found = []
    for svc_name, (label, default_port) in ml_urls.items():
        if svc_name in services:
            # Try to extract actual port from compose spec
            ports = services[svc_name].get("ports", [])
            port = default_port
            if ports:
                port_str = str(ports[0]).split(":")[0]
                try:
                    port = int(port_str)
                except ValueError:
                    pass
            found.append((label, f"http://localhost:{port}"))
    
    if found:
        table = Table(title="ML & Observability Dashboards", show_header=True)
        table.add_column("Service", style="cyan")
        table.add_column("URL", style="bold green")
        for label, url in found:
            table.add_row(label, url)
        console.print("\n")
        console.print(table)


def _display_ngrok_tunnel() -> None:
    """Attempt to fetch and display the public Ngrok url from the local agent."""
    import requests
    import time
    
    with console.status("[info]Waiting for ngrok tunnel to establish...[/info]"):
        # Give the tunnel a few seconds to register with the ngrok cloud
        time.sleep(3)
        try:
            response = requests.get("http://localhost:4040/api/tunnels", timeout=2)
            if response.status_code == 200:
                tunnels = response.json().get("tunnels", [])
                for t in tunnels:
                    console.print(f"\\n[success]🌐 Public URL (ngrok):[/success] [bold cyan]{t.get('public_url')}[/bold cyan]")
        except Exception:
            pass

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
        _ensure_binary("helm", "Visit https://helm.sh/docs/intro/install/")
        subprocess.run(["helm", "upgrade", "--install", "app", "."], check=True, cwd=str(helm_dir))
    elif k8s_dir.exists():
        console.print("[success]🚀 Deploying via Kubectl...[/success]\n")
        _ensure_binary("kubectl", "Visit https://kubernetes.io/docs/tasks/tools/")
        subprocess.run(["kubectl", "apply", "-f", "."], check=True, cwd=str(k8s_dir))
    else:
        console.print("[error]✗ No K8s or Helm files found.[/error]")

def _up_cloud(project_dir: Path, target: str) -> None:
    tf_dir = project_dir / "infra" / "terraform"
    if not tf_dir.exists():
        console.print("[error]✗ Terraform files not found.[/error]")
        raise SystemExit(1)

    console.print(f"[success]🚀 Provisioning Cloud Infrastructure ({target})...[/success]\n")
    _ensure_binary("terraform", "Visit https://developer.hashicorp.com/terraform/downloads")
    subprocess.run(["terraform", "init"], check=True, cwd=str(tf_dir))
    subprocess.run(["terraform", "apply", "-auto-approve"], check=True, cwd=str(tf_dir))
