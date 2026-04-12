from pathlib import Path

import typer
from rich.prompt import Confirm, Prompt
from rich.table import Table

from nikame.cli.output import console, print_header, print_section, print_success
from nikame.engines.rollback import RollbackEngine

app = typer.Typer(help="Rollback project to a previous snapshot.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    project_root: Path | None = typer.Option(None, "--root", help="Project root directory")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    actual_root = project_root or Path.cwd()
    print_header("Snapshot Rollback")
    
    engine = RollbackEngine(actual_root)
    snapshots = engine.list_snapshots()
    
    if not snapshots:
        console.print("[warning]No snapshots found.[/]")
        return
        
    print_section("Available Snapshots")
    
    table = Table.grid(padding=(0, 2))
    table.add_column("#", style="text_muted", width=4)
    table.add_column("ID", style="accent", width=30)
    table.add_column("Created", style="text_secondary")
    
    for i, snap_id in enumerate(snapshots, 1):
        # Extract timestamp from ID for display
        # ID format: snap_YYYYMMDD_HHMMSS
        parts = snap_id.split("_")
        created = "unknown"
        if len(parts) >= 3:
            date_str = parts[1]
            time_str = parts[2]
            created = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}"
            
        table.add_row(str(i), snap_id, created)
        
    console.print(table)
    console.print("─" * 60)
    
    choice = Prompt.ask("Select snapshot [#] or [q] quit", default="q")
    if choice.lower() == "q":
        return
        
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(snapshots):
            raise ValueError
        selected_snap = snapshots[idx]
    except (ValueError, IndexError):
        console.print("[danger]Invalid selection.[/]")
        return
        
    if Confirm.ask(f"[warning]Confirm rollback to {selected_snap}?[/]", default=False):
        engine.restore_snapshot(selected_snap)
        print_success(f"Project successfully rolled back to {selected_snap}.")
