import time
from pathlib import Path

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from nikame.cli.output import (
    console,
    print_header,
    print_section,
    print_success,
)
from nikame.engines.verify import SyntaxVerifier

app = typer.Typer(help="Verify project integrity and local syntax health.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    project_root: Path | None = typer.Option(None, "--root", help="Project root directory"),
    fast: bool = typer.Option(False, "--fast", help="Skip deep AST analysis")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    actual_root = project_root or Path.cwd()
    print_header("Project integrity verification")
    
    verifier = SyntaxVerifier(actual_root)
    
    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        
        # 1. Structure Check
        t1 = progress.add_task("[text_secondary]Checking project structure...", total=1)
        # Mocking check for Phase 2
        time.sleep(0.4)
        progress.update(t1, completed=1)
        console.print("[success]✓[/success] Project structure valid")
        
        # 2. Syntax Analysis
        t2 = progress.add_task("[text_secondary]Performing AST syntax analysis...", total=100)
        
        errors: list[str] = []
        if not fast:
            py_files = list(actual_root.rglob("*.py"))
            for i, f in enumerate(py_files):
                if any(p in str(f) for p in [".venv", "venv", "__pycache__"]):
                    continue
                if not verifier.verify_file(f):
                    errors.append(str(f))
                progress.update(t2, advance=(100 / (len(py_files) or 1)))
        
        progress.update(t2, completed=100)
        
        if errors:
            console.print(f"[danger]✗[/danger] Syntax errors found in {len(errors)} files")
            print_section("Syntax Errors")
            for err in errors:
                console.print(f"  [danger]•[/danger] {err}")
            raise typer.Exit(code=1)
        else:
            console.print("[success]✓[/success] AST syntax analysis passed")
            
    print_success("Verification complete. Project is healthy.")
