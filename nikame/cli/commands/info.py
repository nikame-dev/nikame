import typer
from nikame.cli.output import print_info

app = typer.Typer(help="Inspect pattern manifests and metadata.")

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    pattern_id: str = typer.Argument(..., help="Pattern ID to inspect")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    print_info(f"Metadata for {pattern_id} not implemented yet.")
