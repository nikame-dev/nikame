from pathlib import Path

import typer
from rich.table import Table

from nikame.cli.output import console, print_header, print_section
from nikame.core.registry.loader import RegistryLoader

app = typer.Typer(help="List and search available patterns in the registry.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
    registry_path: Path = typer.Option(Path("registry"), "--registry", help="Path to pattern registry")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    print_header("Pattern Registry")
    
    loader = RegistryLoader(registry_path)
    patterns = loader.load_all()
    
    if not patterns:
        console.print("[warning]No patterns found in registry.[/]")
        return
        
    categories = sorted({p.category for p in patterns})
    if category:
        categories = [c for c in categories if c == category]
        
    for cat in categories:
        print_section(cat.capitalize())
        
        table = Table.grid(padding=(0, 2))
        table.add_column("ID", style="accent", width=20)
        table.add_column("Version", style="text_muted", width=8)
        table.add_column("Name", style="text_primary")
        
        cat_patterns = [p for p in patterns if p.category == cat]
        for p in cat_patterns:
            table.add_row(p.id, f"v{p.version}", p.display_name)
            
        console.print(table)
        
    console.print(f"\n[text_muted]-- {len(patterns)} patterns total  ·  nikame.dev/patterns --[/]")
