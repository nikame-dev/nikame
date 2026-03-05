"""nikame remove — Remove a module or feature from an existing project.

Modifies nikame.yaml and triggers cleanup.
"""

from __future__ import annotations

from pathlib import Path

import click
import yaml

from nikame.codegen.base import CodegenContext
from nikame.codegen.registry import discover_codegen, get_codegen_class
from nikame.codegen.wiring import WiringManager
from nikame.utils.logger import console


@click.command()
@click.argument("name")
@click.option(
    "--project-dir", "-d",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory containing nikame.yaml.",
)
def remove(name: str, project_dir: Path) -> None:
    """Remove a module or feature from the current project.

    Example: 
        nikame remove graphql
    """
    config_path = project_dir / "nikame.yaml"
    if not config_path.exists():
        console.print(f"[error]nikame.yaml not found in {project_dir}[/error]")
        raise SystemExit(1)

    # 1. Load existing config
    with open(config_path) as f:
        config_data = yaml.safe_load(f)

    # 2. Check if it exists in features
    if "features" in config_data and name in config_data["features"]:
        discover_codegen()
        codegen_cls = get_codegen_class(name)

        if codegen_cls:
            # A. Performance Cleanup (Wiring)
            with console.status(f"[info]Removing wiring for {name}...[/info]"):
                # We need context to get the correct wiring info
                ctx = CodegenContext(
                    project_name=config_data.get("name", "app"),
                    active_modules=[], # Not strictly needed for removal usually
                    features=config_data["features"]
                )
                generator = codegen_cls(ctx, None)
                wiring_info = generator.wiring()

                manager = WiringManager(project_dir)
                manager.remove(wiring_info)

            # B. Remove from config
            config_data["features"].remove(name)
            console.print(f"[info]Removed feature [module]{name}[/module] from nikame.yaml.[/info]")

            # C. Save
            with open(config_path, "w") as f:
                yaml.dump(config_data, f, sort_keys=False)

            console.print(f"\n[success]✓ [module]{name}[/module] removed successfully.[/success]")
            console.print("[note]Note: Generated files for this feature were NOT deleted. You may remove them manually from app/ if no longer needed.[/note]")
        else:
            console.print(f"[error]Feature '{name}' found in config but not in registry.[/error]")
    else:
        # Check modules (databases, etc - removal of infrastructure is more complex,
        # for now we focus on features/components)
        console.print(f"[error]Feature '{name}' not found in nikame.yaml.[/error]")
        raise SystemExit(1)
