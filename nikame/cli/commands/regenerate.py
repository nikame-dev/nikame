import click
from pathlib import Path
from nikame.config.loader import load_config
from nikame.codegen.schema_codegen import SchemaCodegen
from nikame.utils.logger import console


@click.command(name="regenerate")
@click.option("--dir", "project_dir", type=click.Path(exists=True), default=".", help="Project directory.")
def regenerate(project_dir: str) -> None:
    """Re-runs the full codegen pipeline against nikame.yaml models."""
    path = Path(project_dir).resolve()
    config_file = path / "nikame.yaml"
    
    if not config_file.exists():
        console.print(f"[error]No nikame.yaml found in {path}[/error]")
        return

    try:
        config = load_config(config_file)
        console.print(f"[info]Regenerating stack for project: [key]{config.name}[/key]...[/info]")
        
        # In Phase 4, we only regenerate schema-driven code for now
        if config.models:
            codegen = SchemaCodegen(config)
            codegen.generate(path)
            console.print("[success]✓ Full stack regenerated successfully.[/success]")
        else:
            console.print("[warning]No models defined in nikame.yaml. Nothing to regenerate.[/warning]")
            
    except Exception as e:
        console.print(f"[error]Regeneration failed: {e}[/error]")
