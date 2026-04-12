from pathlib import Path

import typer
from rich.syntax import Syntax

from nikame.cli.output import console, print_header, print_section

app = typer.Typer(help="Preview changes for a pattern or project.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    pattern_id: str = typer.Argument(..., help="Pattern ID to diff"),
    project_root: Path | None = typer.Option(None, "--root", help="Project root directory")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    actual_root = project_root or Path.cwd()
    print_header(f"Diff Preview: {pattern_id}")
    
    # In Phase 2, this is a placeholder/mock. 
    # In Phase 3, this will use ScaffoldEngine.prepare_diff()
    print_section("app/api/auth/router.py")
    diff_content = """
+ from fastapi import APIRouter
+ 
+ router = APIRouter(prefix="/auth")
+ 
+ @router.post("/login")
+ async def login():
+     return {"message": "login"}
"""
    syntax = Syntax(diff_content.strip(), "python", theme="monokai", line_numbers=True)
    console.print(syntax)
    console.print("\n[text_muted]-- Showing mock diff for Phase 2 CLI demo --[/]")
