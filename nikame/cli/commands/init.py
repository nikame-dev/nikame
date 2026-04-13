from pathlib import Path
from typing import Any

import typer
import yaml
from rich.prompt import Prompt

from nikame.cli.output import console, print_header, print_section, print_success

app = typer.Typer(help="Initialize a new NIKAME project.")


def _generate_project(name: str, description: str, modules: list[str], profile: str = "local") -> None:
    """Core logic to generate project files."""
    # Create nikame.yaml
    config = {
        "version": "2.0",
        "name": name,
        "description": description,
        "modules": modules,
        "environment": {
            "target": profile
        }
    }
    
    config_path = Path("nikame.yaml")
    config_path.write_text(yaml.dump(config, sort_keys=False))
    
    # Create .nikame directory and initial manifest
    dot_nikame = Path(".nikame")
    dot_nikame.mkdir(exist_ok=True)
    
    print_success(f"Created {config_path}")
    print_success("Initialized .nikame/ context directory")
    
    from rich.panel import Panel
    summary = (
        f"[bold accent]Project:[/] {name}\n"
        f"[bold accent]Environment:[/] {profile.upper()}\n"
        f"[bold accent]Modules:[/] {', '.join(modules) if modules else 'None'}\n\n"
        "Run `[success]nikame verify[/]` to check health."
    )
    console.print()
    console.print(Panel(summary, title="[success]✨ Project initialized successfully![/]", border_style="success", expand=False))


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    name: str | None = typer.Argument(None, help="Project name"),
    description: str | None = typer.Option(None, "--description", "-d", help="Project description"),
    modules: str | None = typer.Option(None, "--modules", "-m", help="Comma-separated modules"),
    tui: bool = typer.Option(False, "--tui", "-t", help="Launch interactive UI wizard")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    print_header("Project Initializer")
    
    if tui:
        # Launch Textual Init Wizard
        from textual.app import App
        from nikame.tui.screens.init_wizard import InitWizard
        
        from nikame.tui.theme import get_css_variables_str
        
        class WizardLauncher(App[dict[str, Any]]):
            CSS = get_css_variables_str()

            def on_mount(self) -> None:
                self.push_screen(InitWizard())
        
        launcher = WizardLauncher()
        result = launcher.run()
        
        # Ensure Textual buffer is fully flushed and terminal is reset
        import os
        import time
        time.sleep(0.05)
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print_header("Project Initializer")
        
        if result:
            _generate_project(
                name=result["name"],
                description=result["description"],
                modules=result["modules"],
                profile=result["profile"]
            )
        else:
            console.print("[warning]Initialization cancelled.[/]")
            console.print()
        return

    # Standard CLI Prompts (Fallback/Classic)
    if not name:
        name = Prompt.ask("[text_primary]Project Name[/]", default="my-fastapi-app")
        
    if not description:
        description = Prompt.ask("[text_primary]Description[/]", default="A production FastAPI application")
    
    if modules is None:
        print_section("Features")
        console.print("[text_secondary]Available core modules:[/]")
        console.print("  • database.postgres")
        console.print("  • cache.redis")
        console.print("  • auth.jwt")
        
        modules_str = Prompt.ask("[text_primary]Modules to include (comma-separated)[/]", default="database.postgres,auth.jwt")
        modules_list = [m.strip() for m in modules_str.split(",") if m.strip()]
    else:
        modules_list = [m.strip() for m in modules.split(",") if m.strip()]
    
    _generate_project(name, description, modules_list)
