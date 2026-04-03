"""Infrastructure deployment commands for NIKAME."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

import click
import yaml
from rich.console import Console

from nikame.blueprint.engine import build_blueprint
from nikame.utils.logger import console

if TYPE_CHECKING:
    from nikame.config.schema import NikameConfig


@click.command()
@click.option("--target", "-t", default="local", help="Deployment target (local, kubernetes, cloud)")
@click.option("--service", "-s", multiple=True, help="Specific service to start")
@click.option("--build", is_flag=True, help="Force rebuild of containers")
@click.option("--detach", is_flag=True, default=True, help="Run in background")
@click.pass_context
def up(ctx: click.Context, target: str, service: tuple[str, ...], build: bool, detach: bool) -> None:
    """Start generated infrastructure services."""
    project_dir = Path.cwd()
    config_file = project_dir / "nikame.yaml"

    if not config_file.exists():
        console.print("[red]✗ nikame.yaml not found. Are you in a NIKAME project?[/red]")
        raise SystemExit(1)

    from nikame.config.loader import load_config
    config = load_config(config_file)

    if target == "local":
        _up_local(project_dir, config, service, build, detach)
    elif target == "kubernetes":
        _up_k8s(project_dir)
    else:
        console.print(f"[error]✗ Target '{target}' not yet supported for 'up'[/error]")


def _up_local(project_dir: Path, config: NikameConfig, service: tuple[str, ...], build: bool, detach: bool) -> None:
    """Start services locally using Docker Compose with phase-aware ordering."""
    _ensure_binary("docker", "Visit https://docs.docker.com/get-docker/")
    
    compose_file = project_dir / "infra" / "docker-compose.yml"
    if not compose_file.exists():
        console.print("[red]✗ docker-compose.yml not found. Run 'nikame init' first.[/red]")
        raise SystemExit(1)
        
    with open(compose_file) as f:
        compose_data = yaml.safe_load(f)
        
    cmd_base = ["docker", "compose", "-p", config.name, "-f", str(compose_file)]
    env_file = project_dir / ".env.generated"
    if env_file.exists():
        cmd_base.extend(["--env-file", str(env_file)])
    
    # ── ML-Aware Dependency Ordering ──
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
        
        console.print("\n🚀 [bold]Starting Local Services (Docker Compose)...[/bold]\n")
        
        for label, svcs in phases:
            if svcs:
                console.print(f"  [info]{label}:[/info] {', '.join(svcs)}")
                phase_cmd = cmd_base + ["up", "-d"]
                if build: phase_cmd.append("--build")
                phase_cmd.extend(svcs)
                try:
                    subprocess.run(phase_cmd, check=True, cwd=str(project_dir))
                    time.sleep(2)
                except subprocess.CalledProcessError:
                    console.print(f"\n[error]✗ Phase failed: {label}[/error]")
                    raise SystemExit(1)
    else:
        cmd = cmd_base + ["up"]
        if detach: cmd.append("-d")
        if build: cmd.append("--build")
        cmd.extend(service)
        try:
            subprocess.run(cmd, check=True, cwd=str(project_dir))
        except subprocess.CalledProcessError:
            console.print("\n[error]✗ Docker Compose failed to start services.[/error]")
            raise SystemExit(1)

    # Health Checks & Summary
    _verify_health(config.name)
    _print_ml_urls(compose_data)
    
    blueprint = build_blueprint(config)
    if "ngrok" in [m.NAME for m in blueprint.modules]:
        _display_ngrok_tunnel()


def _ensure_binary(binary: str, hint: str) -> None:
    """Ensure a binary is installed and executable."""
    try:
        subprocess.run([binary, "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(f"[error]✗ '{binary}' not found.[/error]")
        console.print(f"[dim]{hint}[/dim]")
        raise SystemExit(1)


def _verify_health(project_name: str) -> None:
    """Simple health check summary."""
    console.print(f"\n[info]Checking service status for {project_name}...[/info]")
    try:
        # We rely on nikame.utils.docker if available, else just a print
        from nikame.utils.docker import get_project_containers
        containers = get_project_containers(project_name)
        if containers:
            console.print(f"✨ {len(containers)} containers detected.")
    except ImportError:
        pass


def _print_ml_urls(compose_data: dict) -> None:
    """Print ML-specific UI URLs."""
    pass


def _display_ngrok_tunnel() -> None:
    """Display Ngrok URL."""
    pass


def _up_k8s(project_dir: Path) -> None:
    """Kubernetes deployment."""
    pass
