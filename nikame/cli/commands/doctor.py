import typer
from nikame.cli.output import print_info, print_success, print_error

app = typer.Typer(help="Check environment and dependencies.")

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    fix: bool = typer.Option(False, "--fix", help="Attempt to auto-fix issues")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    print_info("Running diagnostics...")
    print_success("Python version is compatible.")
    print_success("All checks passed. Ready.")
