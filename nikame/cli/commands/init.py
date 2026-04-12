import typer
from pathlib import Path
from nikame.cli.output import print_success, print_error, print_info
from typing import Optional

app = typer.Typer(help="Initialize a new NIKAME project or environment.")

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to nikame.yaml"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Run interactive TUI wizard")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    if config:
        print_info(f"Initializing from config: {config}")
        # non-interactive flow using config loader
    else:
        if interactive:
            print_info("Starting Interactive Wizard (TUI)...")
            # Trigger textual UI
        else:
            print_error("Must provide --config when running non-interactively.")
            raise typer.Exit(1)
