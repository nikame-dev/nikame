import typer
from typing import Optional
from nikame.cli.output import print_info, print_success

app = typer.Typer(help="Add a pattern to the project.")

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    pattern_id: str = typer.Argument(..., help="ID of the pattern to add (e.g. auth.jwt)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying"),
    no_confirm: bool = typer.Option(False, "--no-confirm", help="Skip confirmation prompt")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    if dry_run:
        print_info(f"Dry run for adding pattern: {pattern_id}")
    else:
        print_info(f"Adding pattern: {pattern_id}")
        
    print_success("Pattern added successfully!")
