from pathlib import Path

import typer

from nikame.cli.output import print_info

app = typer.Typer(help="Launch the autonomous agent (TUI).")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    project_root: Path | None = typer.Option(None, "--root", help="Project root directory"),
    model: str = typer.Option("qwen2.5-coder:7b", "--model", help="LLM model to use"),
    provider: str = typer.Option("ollama", "--provider", help="LLM provider (ollama, openai, etc)")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    actual_root = project_root or Path.cwd()
    print_info(f"Starting agent with {provider} / {model}...")
    
    # Launch Textual TUI
    from nikame.tui.app import NikameApp
    
    tui_app = NikameApp(project_root=actual_root)
    tui_app.run()
