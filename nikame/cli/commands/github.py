"""GitHub lifecycle management commands for NIKAME.

Commands for syncing code, managing secrets, and rotating credentials.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import anyio
import click
import questionary
from rich.table import Table

from nikame.utils.auth import credentials
from nikame.utils.github_client import GitHubClient
from nikame.utils.git import git_push, get_project_metadata, save_project_metadata
from nikame.utils.logger import console


@click.group()
def github() -> None:
    """Manage GitHub integration and GitOps lifecycle."""
    pass


@github.command()
@click.option("--remote", default="origin", help="Git remote to push to.")
@click.option("--branch", default="main", help="Branch to push.")
def sync(remote: str, branch: str) -> None:
    """Re-push current state and re-sync all secrets."""
    token = credentials.get_github_token()
    if not token:
        console.print("[error]Not logged in to GitHub. Run 'nikame login'.[/error]")
        return

    metadata = get_project_metadata(Path("."))
    owner = metadata.get("github_owner")
    repo_name = metadata.get("github_repo")

    if not owner or not repo_name:
        console.print("[error]No GitHub metadata found for this project. Was it initialized with GitHub?[/error]")
        return

    console.print(f"[info]Syncing project to {owner}/{repo_name}...[/info]")
    
    # 1. Push code
    try:
        git_push(Path("."), remote=remote, branch=branch)
        console.print("[success]✓ Code synced to GitHub.[/success]")
    except Exception as e:
        console.print(f"[error]Git push failed: {e}[/error]")

    # 2. Sync secrets
    _sync_secrets_logic(owner, repo_name, token)


@github.group()
def secrets() -> None:
    """Manage GitHub Actions secrets."""
    pass


@secrets.command(name="list")
def list_secrets() -> None:
    """List names of secrets injected into the repository."""
    token = credentials.get_github_token()
    metadata = get_project_metadata(Path("."))
    owner = metadata.get("github_owner")
    repo = metadata.get("github_repo")

    if not token or not owner or not repo:
        console.print("[error]Insufficient GitHub context. Are you logged in and in a NIKAME project?[/error]")
        return

    client = GitHubClient(token)
    try:
        secret_names = anyio.run(client.list_secrets, owner, repo)
        if not secret_names:
            console.print("[info]No secrets found in this repository.[/info]")
            return

        table = Table(title=f"Secrets in {owner}/{repo}")
        table.add_column("Secret Name", style="cyan")
        for name in secret_names:
            table.add_row(name)
        console.print(table)
    except Exception as e:
        console.print(f"[error]Failed to list secrets: {e}[/error]")


@secrets.command(name="add")
@click.argument("kv_pair")
def add_secret(kv_pair: str) -> None:
    """Inject a single new secret. Format: KEY=VALUE."""
    if "=" not in kv_pair:
        console.print("[error]Invalid format. Use KEY=VALUE[/error]")
        return

    key, val = kv_pair.split("=", 1)
    token = credentials.get_github_token()
    metadata = get_project_metadata(Path("."))
    owner = metadata.get("github_owner")
    repo = metadata.get("github_repo")

    if not token or not owner or not repo:
        console.print("[error]Insufficient GitHub context.[/error]")
        return

    client = GitHubClient(token)
    try:
        with console.status(f"[info]Injecting secret {key}...[/info]"):
            success = anyio.run(client.set_secret, owner, repo, key, val)
            if success:
                console.print(f"[success]✓ Secret '{key}' injected.[/success]")
            else:
                console.print(f"[error]Failed to inject secret '{key}'.[/error]")
    except Exception as e:
        console.print(f"[error]Error: {e}[/error]")


@secrets.command(name="rotate")
def rotate_secrets() -> None:
    """Regenerate all auto-generated secrets and re-inject."""
    confirm = questionary.confirm("This will regenerate all passwords in .env.generated and update GitHub. Continue?").ask()
    if not confirm:
        return

    # In a real scenario, we'd trigger a new .env.generated write
    # For now, we'll suggest running nikame init again or implement logic here.
    console.print("[info]Rotation logic would regenerate .env.generated and call sync_secrets.[/info]")
    console.print("[warning]Full rotation not yet implemented in this preview.[/warning]")


def _sync_secrets_logic(owner: str, repo: str, token: str) -> None:
    """Internal helper to sync secrets from .env.generated."""
    client = GitHubClient(token)
    env_gen = Path(".env.generated")
    if not env_gen.exists():
        console.print("[warning].env.generated not found. No secrets to sync.[/warning]")
        return

    with console.status("[info]Checking and injecting secrets...[/info]"):
        results = {"injected": 0, "skipped_empty": 0, "skipped_exists": 0, "failed": 0}
        
        for line in env_gen.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip()
                
                if not val or "your-key-here" in val:
                    results["skipped_empty"] += 1
                    continue
                
                try:
                    exists = anyio.run(client.get_secret, owner, repo, key)
                    if exists:
                        overwrite = questionary.confirm(f"Secret '{key}' already exists. Overwrite?", default=False).ask()
                        if not overwrite:
                            results["skipped_exists"] += 1
                            continue
                            
                    success = anyio.run(client.set_secret, owner, repo, key, val)
                    if success:
                        results["injected"] += 1
                    else:
                        results["failed"] += 1
                except Exception as e:
                    console.print(f"[error]Error syncing {key}: {e}[/error]")
                    results["failed"] += 1

        console.print(f"\n[success]Sync Summary for {owner}/{repo}:[/success]")
        console.print(f"  Injected: {results['injected']}")
        console.print(f"  Already existed: {results['skipped_exists']} (kept)")
        console.print(f"  Empty/Placeholder: {results['skipped_empty']} (skipped)")
        if results["failed"]:
            console.print(f"  [error]Failed: {results['failed']}[/error]")
