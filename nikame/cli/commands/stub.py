from pathlib import Path

import typer
from rich.syntax import Syntax

from nikame.cli.output import console, print_header
from nikame.core.ast.stubber import generate_stub

app = typer.Typer(help="Generate compact AST stubs for LLM context.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    path: Path = typer.Argument(..., help="Path to the file or directory to stub")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    print_header("AST Stub Generator")
    
    if path.is_dir():
        for py_file in path.rglob("*.py"):
            _stub_file(py_file)
    else:
        _stub_file(path)


def _stub_file(path: Path) -> None:
    console.print(f"[section]Stub for {path} [/]" + "─" * 30)
    stub = generate_stub(path)
    syntax = Syntax(stub, "python", theme="monokai", line_numbers=False)
    console.print(syntax)
    console.print("\n")
