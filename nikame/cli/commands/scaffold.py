"""nikame scaffold — Production pattern scaffolding.

Integrates fastcheat pattern scaffolding into NIKAME.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from nikame.scaffold.core.registry import get_registry
from nikame.scaffold.core.scaffolder import get_scaffolder
from nikame.scaffold.core.renderer import render_scaffold_result, render_pattern_info, render_pattern_table

console = Console()

@click.group(name="scaffold")
def scaffold_group():
    """Production pattern scaffolding & code reference."""
    pass

@scaffold_group.command(name="add")
@click.argument("pattern")
@click.argument("target", type=click.Path(exists=False, path_type=Path))
@click.option("--var", "-v", multiple=True, help="Variable override: --var KEY=VALUE")
@click.option("--dry-run", is_flag=True, help="Preview without writing")
@click.option("--force", "-f", is_flag=True, help="Overwrite without prompting")
def scaffold_add(pattern: str, target: Path, var: tuple[str, ...], dry_run: bool, force: bool) -> None:
    """Scaffold a pattern into your project."""
    registry = get_registry()
    meta = registry.get(pattern)

    if meta is None:
        console.print(f"[red]✗[/red] Pattern [bold]'{pattern}'[/bold] not found.")
        console.print("[dim]Run 'nikame scaffold list' to see available patterns.[/dim]")
        raise SystemExit(1)

    # Parse variable overrides
    var_overrides: dict[str, str] = {}
    if var:
        for v in var:
            if "=" not in v:
                console.print(f"[red]✗[/red] Invalid --var format: '{v}'. Use KEY=VALUE.")
                raise SystemExit(1)
            key, value = v.split("=", 1)
            var_overrides[key.strip()] = value.strip()

    # Ensure target directory exists
    target = target.resolve()
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    scaffolder = get_scaffolder()

    mode = "[dim](dry run)[/dim]" if dry_run else ""
    console.print(f"\n[cyan]▸[/cyan] Scaffolding [bold]{meta.name}[/bold] → {target} {mode}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Scaffolding...", total=None)
        result = scaffolder.scaffold(
            slug=pattern,
            target_dir=target,
            var_overrides=var_overrides,
            force=force,
            dry_run=dry_run,
        )
        progress.update(task, completed=True)

    if result:
        render_scaffold_result(result)

    if dry_run:
        console.print("[dim]No files were modified (dry run).[/dim]")

@scaffold_group.command(name="info")
@click.argument("pattern")
def scaffold_info(pattern: str) -> None:
    """Show detailed info for a pattern."""
    registry = get_registry()
    meta = registry.get(pattern)

    if meta is None:
        console.print(f"[red]✗[/red] Pattern [bold]'{pattern}'[/bold] not found.")
        suggestions = registry.search(pattern, threshold=50)
        if suggestions:
            console.print("\n[dim]Did you mean:[/dim]")
            for s in suggestions[:5]:
                console.print(f"  [cyan]{s.slug}[/cyan] — {s.description[:60]}")
        raise SystemExit(1)

    render_pattern_info(meta)

@scaffold_group.command(name="list")
@click.option("--category", "-c", help="Filter by category")
@click.option("--tag", "-t", help="Filter by tag")
def scaffold_list(category: Optional[str], tag: Optional[str]) -> None:
    """List all available patterns."""
    registry = get_registry()

    if category:
        patterns = registry.by_category(category)
        title = f"Patterns — {category}"
    elif tag:
        patterns = registry.by_tag(tag)
        title = f"Patterns — tag:{tag}"
    else:
        patterns = registry.all()
        title = "All Available Patterns"

    if not patterns:
        console.print("[yellow]No patterns found.[/yellow]")
        return

    render_pattern_table(patterns, title=title)

@scaffold_group.command(name="search")
@click.argument("query")
def scaffold_search(query: str) -> None:
    """Fuzzy search across all patterns."""
    registry = get_registry()
    results = registry.search(query, threshold=40)

    if not results:
        console.print(f"[yellow]No patterns matching '{query}'.[/yellow]")
        return

    render_pattern_table(results, title=f"Search results for '{query}'")
