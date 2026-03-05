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

    subprocess.run(cmd, check=True, cwd=str(project_dir))

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
