from pathlib import Path

import typer
from rich.table import Table

from nikame.cli.output import console, print_header, print_section
from nikame.engines.doctor import DoctorEngine

app = typer.Typer(help="Check environment and dependencies.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    project_root: Path | None = typer.Option(None, "--root", help="Project root directory")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    actual_root = project_root or Path.cwd()
    print_header("Doctor diagnostics")
    print_section("Environment Check")
    
    engine = DoctorEngine(actual_root)
    checks = engine.run_all()
    
    table = Table.grid(padding=(0, 2))
    table.add_column("Check", style="text_primary")
    table.add_column("Version", style="text_secondary")
    table.add_column("Status", justify="right")
    
    all_passed = True
    for check in checks:
        status_icon = "[success]✓[/success]" if check.status else "[danger]✗[/danger]"
        if not check.status:
            all_passed = False
            
        version_text = check.version if check.version else check.message
        table.add_row(check.name, version_text, status_icon)
        
    console.print(table)
    console.print("\n")
    
    if all_passed:
        console.print("[section]── All checks passed [/]" + "─" * 30)
        console.print("\nReady. Run `nikame agent` to start.")
    else:
        console.print("[danger]── Some checks failed [/]" + "─" * 30)
        console.print("\nPlease resolve the issues above before proceeding.")
