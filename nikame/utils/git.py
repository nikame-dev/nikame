"""Git utilities for NIKAME.

Handles repository initialization, remotes, and pushing with progress feedback.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn


def git_init(path: Path) -> None:
    """Initialize a git repository."""
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)


def git_commit(path: Path, message: str) -> None:
    """Commit all changes."""
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=path, check=True, capture_output=True)


def git_add_remote(path: Path, name: str, url: str) -> None:
    """Add a remote to the repository."""
    # Remove if exists
    subprocess.run(["git", "remote", "remove", name], cwd=path, capture_output=True)
    subprocess.run(["git", "remote", "add", name, url], cwd=path, check=True, capture_output=True)


def git_push(path: Path, remote: str = "origin", branch: str = "main") -> None:
    """Push to remote with a progress bar (simulated via rich)."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        task = progress.add_task(f"Pushing to {remote}/{branch}...", total=100)
        
        # In a real scenario, we might parse git push --progress
        # Here we do the push and update progress
        try:
            subprocess.run(
                ["git", "push", "-u", remote, branch],
                cwd=path,
                check=True,
                capture_output=True,
            )
            progress.update(task, completed=100)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git push failed: {e.stderr.decode()}")


def save_project_metadata(path: Path, metadata: dict[str, Any]) -> None:
    """Save project metadata in .nikame/metadata.json."""
    nikame_dir = path / ".nikame"
    nikame_dir.mkdir(exist_ok=True)
    
    metadata_file = nikame_dir / "metadata.json"
    existing = {}
    if metadata_file.exists():
        try:
            existing = json.loads(metadata_file.read_text())
        except json.JSONDecodeError:
            pass
            
    existing.update(metadata)
    metadata_file.write_text(json.dumps(existing, indent=2))


def get_project_metadata(path: Path) -> dict[str, Any]:
    """Load project metadata."""
    metadata_file = path / ".nikame" / "metadata.json"
    if not metadata_file.exists():
        return {}
    try:
        return json.loads(metadata_file.read_text())
    except json.JSONDecodeError:
        return {}
