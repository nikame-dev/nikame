"""nikame add — Add a module or feature to an existing project.

Modifies nikame.yaml and triggers regeneration.
"""

from __future__ import annotations

from pathlib import Path
import click
import yaml

from nikame.cli.commands.init import _generate_project
from nikame.config.loader import load_config
from nikame.modules.registry import discover_modules, get_module_class
from nikame.codegen.registry import discover_codegen, get_codegen_class
from nikame.codegen.wiring import WiringManager
from nikame.codegen.base import CodegenContext
from nikame.utils.logger import console


@click.command()
@click.argument("name")
@click.option(
    "--project-dir", "-d",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory containing nikame.yaml.",
)
def add(name: str, project_dir: Path) -> None:
    """Add a module or feature to the current project.

    Example: 
        nikame add mongodb
        nikame add graphql
    """
    config_path = project_dir / "nikame.yaml"
    if not config_path.exists():
        console.print(f"[error]nikame.yaml not found in {project_dir}[/error]")
        raise SystemExit(1)

    # 1. Load existing config
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    # 2. Check Modules
    discover_modules()
    mod_cls = get_module_class(name)
    
    # 3. Check Components/Features
    discover_codegen()
    codegen_cls = get_codegen_class(name)

    if not mod_cls and not codegen_cls:
        console.print(f"[error]'{name}' not found as a module or feature.[/error]")
        raise SystemExit(1)

    if mod_cls:
        # Module logic
        category = mod_cls.CATEGORY
        if category == "database":
            config_data.setdefault("databases", {})[name] = {}
        elif category == "messaging":
            config_data.setdefault("messaging", {})[name] = {}
        elif category == "api" and name != "fastapi":
            config_data["api"] = {"framework": name}
        elif category == "observability":
            config_data.setdefault("observability", {})["stack"] = "full"
        elif category == "cicd":
            config_data.setdefault("ci_cd", {})[name] = True
        else:
            config_data[name] = {}
        console.print(f"[info]Adding module [module]{name}[/module] to nikame.yaml...[/info]")

    if codegen_cls:
        # Feature logic
        if "features" not in config_data:
            config_data["features"] = []
        if name not in config_data["features"]:
            config_data["features"].append(name)
            console.print(f"[info]Adding feature [module]{name}[/module] to nikame.yaml...[/info]")

    # 4. Save and Reload
    with open(config_path, "w") as f:
        yaml.dump(config_data, f, sort_keys=False)

    nikame_config = load_config(config_path)

    # 5. Full project regeneration
    _generate_project(nikame_config, project_dir)

    # 6. Wiring (Automated Injection)
    if codegen_cls:
        with console.status(f"[info]Wiring {name} into application...[/info]"):
            # We need a context for the generator
            db_url = ""
            # Simple extraction for context
            if "databases" in config_data and "postgres" in config_data["databases"]:
                db_url = "postgres://postgres@localhost:5432/app"
            
            ctx = CodegenContext(
                project_name=nikame_config.name,
                active_modules=list(config_data.get("databases", {}).keys()) + 
                               list(config_data.get("messaging", {}).keys()) +
                               (["fastapi"] if "api" in config_data else []),
                database_url=db_url,
                features=nikame_config.features
            )
            generator = codegen_cls(ctx)
            wiring_info = generator.wiring()
            
            manager = WiringManager(project_dir)
            manager.apply(wiring_info)

    console.print(f"\n[success]✓ [module]{name}[/module] added and wired successfully.[/success]")
