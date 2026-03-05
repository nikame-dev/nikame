"""nikame diff — Detect drift between config and active blueprint.

Compares current nikame.yaml with the generated .nikame/blueprint.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.table import Table

from nikame.blueprint.engine import build_blueprint
from nikame.config.loader import load_config
from nikame.utils.logger import console


@click.command()
@click.option(
    "--project-dir", "-d",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Project directory.",
)
def diff(project_dir: Path) -> None:
    """Detect changes between nikame.yaml and generated infra."""
    config_path = project_dir / "nikame.yaml"
    snapshot_path = project_dir / ".nikame" / "blueprint.json"

    if not config_path.exists():
        console.print("[error]nikame.yaml not found.[/error]")
        raise SystemExit(1)
    if not snapshot_path.exists():
        console.print("[error]No blueprint snapshot found. Run 'nikame init' first.[/error]")
        raise SystemExit(1)

    # Load current state
    config = load_config(config_path)
    current_blueprint = build_blueprint(config)

    # Load snapshot state
    with open(snapshot_path) as f:
        snapshot = json.load(f)

    snapshot_modules = {m["name"] for m in snapshot.get("modules", [])}
    current_modules = {m.NAME for m in current_blueprint.modules}

    snapshot_features = set(snapshot.get("features", []))
    current_features = set(current_blueprint.active_features)

    # Compare
    added_mod = current_modules - snapshot_modules
    removed_mod = snapshot_modules - current_modules

    added_feat = current_features - snapshot_features
    removed_feat = snapshot_features - current_features

    if not any([added_mod, removed_mod, added_feat, removed_feat]):
        console.print("[success]✓ No drift detected. Config matches infra.[/success]")
        return

    table = Table(title="Drift Detection", box=None)
    table.add_column("Type", style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="bold")

    for mod in added_mod:
        table.add_row("Module", mod, "[green]ADDED[/green]")
    for mod in removed_mod:
        table.add_row("Module", mod, "[red]REMOVED[/red]")

    for feat in added_feat:
        table.add_row("Feature", feat, "[green]ADDED[/green]")
    for feat in removed_feat:
        table.add_row("Feature", feat, "[red]REMOVED[/red]")

    console.print(table)
    console.print("\n[warning]Run 'nikame init' to apply these changes.[/warning]")
