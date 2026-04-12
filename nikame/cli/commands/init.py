from pathlib import Path

import typer
import yaml
from rich.prompt import Prompt

from nikame.cli.output import console, print_header, print_section, print_success

app = typer.Typer(help="Initialize a new NIKAME project.")


def _generate_project(name: str, description: str, modules: list[str]) -> None:
    """Core logic to generate project files."""
    # Create nikame.yaml
    config = {
        "version": "2.0",
        "name": name,
        "description": description,
        "modules": modules,
        "environment": {
            "target": "local"
        }
    }
    
    config_path = Path("nikame.yaml")
    config_path.write_text(yaml.dump(config, sort_keys=False))
    
    # Create .nikame directory and initial manifest
    dot_nikame = Path(".nikame")
    dot_nikame.mkdir(exist_ok=True)
    
    print_success(f"Created {config_path}")
    print_success("Initialized .nikame/ context directory")
    console.print("\n[success]✨ Project initialized successfully![/]")
    console.print("Run `[accent]nikame verify[/]` to check health.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    name: str | None = typer.Argument(None, help="Project name"),
    tui: bool = typer.Option(False, "--tui", "-t", help="Launch interactive UI wizard")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    print_header("Project Initializer")
    
    if tui:
        # Launch Textual Init Wizard
        from typing import Any

        from textual.app import App

        from nikame.tui.screens.init_wizard import InitWizard
        
        class WizardLauncher(App[dict[str, Any]]):
            def on_mount(self) -> None:
                self.push_screen(InitWizard())
        
        launcher = WizardLauncher()
        result = launcher.run()
        
        if result:
            _generate_project(
                name=result["name"],
                description=result["description"],
                modules=result["modules"]
            )
        else:
            console.print("[warning]Initialization cancelled.[/]")
        return

    # Standard CLI Prompts (Fallback/Classic)
    if not name:
        name = Prompt.ask("[text_primary]Project Name[/]", default="my-fastapi-app")
        
    description = Prompt.ask("[text_primary]Description[/]", default="A production FastAPI application")
    
    print_section("Features")
    console.print("[text_secondary]Available core modules:[/]")
    console.print("  • database.postgres")
    console.print("  • cache.redis")
    console.print("  • auth.jwt")
    
    modules_str = Prompt.ask("[text_primary]Modules to include (comma-separated)[/]", default="database.postgres,auth.jwt")
    modules = [m.strip() for m in modules_str.split(",") if m.strip()]
    
    _generate_project(name, description, modules)
