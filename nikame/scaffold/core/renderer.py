"""
nikame scaffold renderer — Rich CLI output for patterns.

Provides beautiful tables, info panels, and scaffold summaries.
"""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from rich.columns import Columns

if TYPE_CHECKING:
    from nikame.scaffold.core.registry import PatternMeta
    from nikame.scaffold.core.scaffolder import ScaffoldResult

console = Console()

def render_pattern_table(patterns: list[PatternMeta], title: str = "Patterns") -> None:
    """Render a collection of patterns as a Rich table."""
    table = Table(title=title, show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Slug", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Category", style="dim")
    table.add_column("Description", ratio=1)
    table.add_column("Diff.", justify="center")

    for p in patterns:
        diff_style = "green" if p.difficulty == "beginner" else "yellow" if p.difficulty == "intermediate" else "red"
        table.add_row(
            p.slug,
            p.name,
            p.category,
            p.description,
            Text(p.difficulty, style=diff_style),
        )

    console.print(table)

def render_pattern_info(p: PatternMeta) -> None:
    """Render detailed information for a single pattern."""
    console.print(Panel(f"[bold cyan]{p.name}[/bold cyan] ([dim]{p.slug}[/dim])", style="magenta"))
    console.print(f"\n[bold]Category:[/bold] {p.category}")
    console.print(f"[bold]Difficulty:[/bold] {p.difficulty}")
    console.print(f"[bold]Description:[/bold] {p.description}")

    if p.tags:
        console.print(f"[bold]Tags:[/bold] {' '.join(f'[blue]#{t}[/blue]' for t in p.tags)}")

    if p.deps:
        console.print(f"\n[bold]Required Packages:[/bold]")
        for dep in p.deps:
            console.print(f"  • {dep}")

    if p.depends_on:
        console.print(f"\n[bold]Pattern Dependencies:[/bold]")
        for dep in p.depends_on:
            console.print(f"  • [cyan]{dep}[/cyan]")

    if p.template_vars:
        console.print(f"\n[bold]Template Variables:[/bold]")
        for var in p.template_vars:
            console.print(f"  • {var}")

    # File Tree
    tree = Tree("\n[bold]File Manifest[/bold]")
    for f in p.files:
        tree.add(f"[green]+[/green] {f.dest} [dim]({f.merge})[/dim]")
    console.print(tree)

    if p.related:
        console.print(f"\n[bold]Related Patterns:[/bold] {', '.join(p.related)}")

def render_scaffold_result(res: ScaffoldResult) -> None:
    """Render a beautiful summary of what was scaffolded."""
    console.print(f"\n[success]✨ Successfully scaffolded [bold]{res.pattern.name}[/bold]![/success]")

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold green")
    summary.add_column()

    if res.files_added:
        summary.add_row("Added:", f"{len(res.files_added)} files")
    if res.files_merged:
        summary.add_row("Merged:", f"{len(res.files_merged)} files")
    if res.deps_installed:
        summary.add_row("Packages:", f"{len(res.deps_installed)} added to requirements.txt")

    console.print(Panel(summary, title="Scaffold Summary", expand=False))

    if res.files_added or res.files_merged:
        console.print("\n[bold]Files:[/bold]")
        for f in res.files_added:
            console.print(f"  [green]✔[/green] {f}")
        for f in res.files_merged:
            console.print(f"  [blue]M[/blue] {f}")

    if res.imports_to_add:
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("Add these imports to your app:")
        for imp in res.imports_to_add:
            console.print(f"  [dim]>>>[/dim] [cyan]{imp}[/cyan]")
