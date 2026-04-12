import typer
from nikame.cli.output import print_info

app = typer.Typer(help="Launch the autonomous agent.")

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    model: str = typer.Option("qwen2.5-coder:7b", "--model", help="LLM model to use"),
    provider: str = typer.Option("ollama", "--provider", help="LLM provider (ollama, openai, etc)")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    print_info(f"Starting agent with {provider} / {model}...")
    # TUI loop goes here
