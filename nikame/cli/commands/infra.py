from pathlib import Path

import typer

from nikame.cli.output import (
    console,
    print_header,
    print_success,
)
from nikame.core.config.loader import ConfigLoader
from nikame.core.manifest.store import ManifestStore
from nikame.infra.docker import ComposeGenerator, DockerfileGenerator

app = typer.Typer(help="Manage project infrastructure.")


@app.command(name="docker", help="Generate production-grade Docker and Compose files.")
def docker_gen(
    project_root: Path | None = typer.Option(None, "--path", help="Project root directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files")
) -> None:
    print_header("Generating Infrastructure")
    
    root = project_root if project_root else Path.cwd()
    
    # 1. Load context
    config_loader = ConfigLoader(root)
    config = config_loader.load()
    if not config:
        console.print("[danger]Error:[/] No [accent]nikame.yaml[/] found in current directory.")
        raise typer.Exit(1)
        
    manifest_store = ManifestStore(root)
    manifest = manifest_store.load()
    if not manifest:
        console.print("[warning]No project manifest found.[/] Generating base infrastructure.")
        # Create a shell manifest if missing
        from datetime import datetime
        from nikame.core.manifest.schema import ManifestV2
        manifest = ManifestV2(
            nikame_version="2.0.0",
            project_name=config.name,
            created_at=datetime.now()
        )
        
    # 2. Generate Dockerfile
    docker_gen = DockerfileGenerator()
    dockerfile_content = docker_gen.generate(config)
    dockerfile_path = root / "Dockerfile"
    
    if dockerfile_path.exists() and not force:
        console.print(f"  [text_muted]Skipping existing [bold]Dockerfile[/][/]")
    else:
        dockerfile_path.write_text(dockerfile_content)
        console.print("  [success]✓[/] Created [bold]Dockerfile[/]")
        
    # 3. Generate docker-compose.yml
    compose_gen = ComposeGenerator()
    compose_content = compose_gen.generate(config, manifest)
    compose_path = root / "docker-compose.yml"
    
    if compose_path.exists() and not force:
        console.print(f"  [text_muted]Skipping existing [bold]docker-compose.yml[/][/]")
    else:
        compose_path.write_text(compose_content)
        console.print("  [success]✓[/] Created [bold]docker-compose.yml[/]")
        
    print_success("Infrastructure generation complete!")


@app.callback()
def main() -> None:
    """Infrastructure orchestration commands."""
    pass
