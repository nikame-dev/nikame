from pathlib import Path

import typer
from rich.table import Table

from nikame.cli.output import console, print_header, print_section
from nikame.core.registry.loader import RegistryLoader

app = typer.Typer(help="Inspect pattern manifests and metadata.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    pattern_id: str = typer.Argument(..., help="Pattern ID to inspect"),
    registry_path: Path = typer.Option(Path("registry"), "--registry", help="Path to pattern registry")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    print_header(f"Pattern Info: {pattern_id}")
    
    loader = RegistryLoader(registry_path)
    pattern = loader.load_pattern(pattern_id)
    
    if not pattern:
        console.print(f"[danger]Error:[/] Pattern [accent]{pattern_id}[/] not found in registry.")
        raise typer.Exit(code=1)
        
    console.print(f"[bold accent]{pattern.display_name}[/] [text_muted]v{pattern.version}[/]")
    console.print(f"[text_primary]{pattern.description}[/]\n")
    
    table = Table.grid(padding=(0, 2))
    table.add_column("Key", style="text_secondary")
    table.add_column("Value", style="text_primary")
    
    table.add_row("Category", pattern.category)
    table.add_row("Author", pattern.author)
    table.add_row("Tags", ", ".join(pattern.tags))
    
    console.print(table)
    
    if pattern.requires:
        print_section("Requires")
        for req in pattern.requires:
            console.print(f"  [warning]•[/] {req}")
            
    if pattern.conflicts:
        print_section("Conflicts")
        for conf in pattern.conflicts:
            console.print(f"  [danger]•[/] {conf}")
            
    if pattern.env_vars:
        print_section("Environment Variables")
        for ev in pattern.env_vars:
            req_str = "[danger](required)[/]" if ev.required else ""
            default_str = f"[text_muted]default: {ev.default}[/]" if ev.default else ""
            console.print(f"  [accent]{ev.name}[/] {req_str} {default_str}")
            if ev.description:
                console.print(f"    [text_secondary]{ev.description}[/]")
    
    console.print("\n")
