"""nikame down — Stop infrastructure services."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click

from nikame.utils.logger import console


@click.command()
@click.option(
    "--volumes", "-v",
    is_flag=True,
    help="Remove named volumes declared in the 'volumes' section of the Compose file and anonymous volumes attached to containers.",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory containing infra/.",
)
@click.pass_context
def down(
    ctx: click.Context,
    volumes: bool,
    project_dir: Path,
) -> None:
    """Stop NIKAME infrastructure services."""
    from nikame.config.loader import load_config
    config_path = project_dir / "nikame.yaml"

    if not config_path.exists():
        console.print("[error]✗ nikame.yaml not found.[/error]")
        raise SystemExit(1)

    config = load_config(config_path)
    target = config.environment.target

    if target == "local":
        _down_local(project_dir, volumes)
    elif target in ["aws", "gcp", "azure"]:
        _down_cloud(project_dir, target)
    elif target == "kubernetes":
        _down_k8s(project_dir)
    else:
        console.print(f"[error]✗ Target '{target}' not yet supported for 'down'[/error]")

def _down_local(project_dir: Path, volumes: bool) -> None:
    compose_file = project_dir / "infra" / "docker-compose.yml"
    if not compose_file.exists():
        console.print("[error]✗ docker-compose.yml not found.[/error]")
        raise SystemExit(1)

    console.print("[info]🛑 Stopping Local Services (Docker Compose)...[/info]\n")
    cmd = ["docker", "compose", "-f", str(compose_file)]
    env_file = project_dir / ".env.generated"
    if env_file.exists(): cmd.extend(["--env-file", str(env_file)])
    cmd.append("down")
    if volumes: cmd.append("-v")

    subprocess.run(cmd, check=True, cwd=str(project_dir))

def _down_k8s(project_dir: Path) -> None:
    k8s_dir = project_dir / "infra" / "kubernetes"
    helm_dir = project_dir / "infra" / "helm"

    if helm_dir.exists():
        console.print("[info]🛑 Removing Helm release...[/info]\n")
        subprocess.run(["helm", "uninstall", "app"], check=True, cwd=str(helm_dir))
    elif k8s_dir.exists():
        console.print("[info]🛑 Removing Kubectl resources...[/info]\n")
        subprocess.run(["kubectl", "delete", "-f", "."], check=True, cwd=str(k8s_dir))
    else:
        console.print("[error]✗ No K8s or Helm files found for removal.[/error]")

def _down_cloud(project_dir: Path, target: str) -> None:
    tf_dir = project_dir / "infra" / "terraform"
    if not tf_dir.exists():
        console.print("[error]✗ Terraform files not found.[/error]")
        raise SystemExit(1)

    console.print(f"[info]🛑 Tearing down Cloud Infrastructure ({target})...[/info]\n")
    subprocess.run(["terraform", "destroy", "-auto-approve"], check=True, cwd=str(tf_dir))
