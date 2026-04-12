import typer
from pathlib import Path
from nikame.cli.output import print_info, print_success, print_error
from nikame.core.ast.graph import SyntaxVerifier

app = typer.Typer(help="Run global health checks and syntax verification.")

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    watch: bool = typer.Option(False, "--watch", help="Re-run on file change"),
    json_out: bool = typer.Option(False, "--json", help="Output in JSON format")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    print_info("Starting pure AST verification...")
    verifier = SyntaxVerifier(root=Path("."))
    result = verifier.verify()
    
    if result.passed:
        print_success(f"Verification passed cleanly in {result.duration_ms:.2f}ms.")
    else:
        print_error(f"Verification failed. Found cycles: {result.cycles}")
