"""nikame destroy — Tear down infrastructure services."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click

from nikame.utils.logger import console


@click.command()
@click.option(
    "--keep-data",
    is_flag=True,
    help="Keep volumes (databases, caches). Only stop containers.",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory containing infra/.",
)
@click.confirmation_option(
    prompt="This will tear down all running services. Continue?",
)
@click.pass_context
def destroy(
    ctx: click.Context,
    keep_data: bool,
    project_dir: Path,
) -> None:
    """Tear down all NIKAME infrastructure services."""
    from nikame.config.loader import load_config
    config_path = project_dir / "nikame.yaml"

    if not config_path.exists():
        console.print("[error]✗ nikame.yaml not found.[/error]")
        raise SystemExit(1)

    config = load_config(config_path)
    target = config.environment.target

    if target == "local":
        _destroy_local(project_dir, keep_data)
    elif target in ["aws", "gcp", "azure"]:
        _destroy_cloud(project_dir, target)
    elif target == "kubernetes":
        _destroy_k8s(project_dir)
    else:
        console.print(f"[error]✗ Target '{target}' not yet supported for 'destroy'[/error]")

def _destroy_local(project_dir: Path, keep_data: bool) -> None:
    compose_file = project_dir / "infra" / "docker-compose.yml"
    if not compose_file.exists():
        console.print("[error]✗ docker-compose.yml not found.[/error]")
        raise SystemExit(1)

    console.print("[warning]🗑️  Destroying Local Services (Docker Compose)...[/warning]\n")
    cmd = ["docker", "compose", "-f", str(compose_file), "down"]
    if not keep_data:
        cmd.append("--volumes")
        console.print("  [warning]Volumes will be removed (databases, caches)[/warning]")
    cmd.append("--remove-orphans")

    subprocess.run(cmd, check=True, cwd=str(project_dir))

def _destroy_k8s(project_dir: Path) -> None:
    k8s_dir = project_dir / "infra" / "kubernetes"
    helm_dir = project_dir / "infra" / "helm"

    if helm_dir.exists():
        console.print("[warning]🗑️  Uninstalling Helm chart...[/warning]\n")
        subprocess.run(["helm", "uninstall", "app"], check=True, cwd=str(helm_dir))
    elif k8s_dir.exists():
        console.print("[warning]🗑️  Deleting K8s resources...[/warning]\n")
        subprocess.run(["kubectl", "delete", "-f", "."], check=True, cwd=str(k8s_dir))
    else:
        console.print("[error]✗ No K8s or Helm files found.[/error]")

def _destroy_cloud(project_dir: Path, target: str) -> None:
    tf_dir = project_dir / "infra" / "terraform"
    if not tf_dir.exists():
        console.print("[error]✗ Terraform files not found.[/error]")
        raise SystemExit(1)

    console.print(f"[warning]🗑️  Destroying Cloud Infrastructure ({target})...[/warning]\n")
    # terraform init not needed if already done, but safe to run
    subprocess.run(["terraform", "init"], check=True, cwd=str(tf_dir))
    subprocess.run(["terraform", "destroy", "-auto-approve"], check=True, cwd=str(tf_dir))
