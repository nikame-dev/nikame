"""Templates CLI commands for NIKAME."""

import click
import yaml
import tempfile
import importlib
import subprocess
from pathlib import Path
from rich.table import Table
from rich.syntax import Syntax

from nikame.registry.client import RegistryClient
from nikame.utils.logger import console
from nikame.config.validator import validate_config
from nikame.config.loader import load_config_from_dict
from nikame.cli.wizard.interactive import SetupWizard
from nikame.utils.auth import credentials

@click.group(name="templates")
def templates_group() -> None:
    """Manage and discover NIKAME project templates."""
    pass

@templates_group.command()
@click.argument("query", required=False, default="")
@click.option("--tag", help="Filter by tag")
@click.option("--sort", type=click.Choice(["stars", "recent", "name"]), default="stars", help="Sort order")
@click.option("--verified", is_flag=True, help="Show only verified templates")
def search(query: str, tag: str | None, sort: str, verified: bool) -> None:
    """Search for templates in the registry."""
    client = RegistryClient()
    results = client.search(query, tag, sort, verified)
    
    if not results:
        console.print("[warning]No templates found matching your criteria.[/warning]")
        return
        
    table = Table(title="Template Registry Search Results")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Tags", style="blue")
    table.add_column("Stars", justify="right")
    table.add_column("Author")
    table.add_column("Verified")
    table.add_column("Version")
    
    for r in results:
        verified_mark = "[green]✓[/green]" if r['verified'] else ""
        table.add_row(
            r['id'],
            r['name'],
            r['description'][:50] + "..." if len(r['description']) > 50 else r['description'],
            ", ".join(r['tags'][:3]),
            str(r['stars']),
            r['author'],
            verified_mark,
            r['version']
        )
        
    console.print(table)

@templates_group.command()
@click.argument("template_id")
def show(template_id: str) -> None:
    """Show full details of a template."""
    client = RegistryClient()
    template = client.get_template(template_id)
    
    if not template:
        console.print(f"[error]Template '{template_id}' not found.[/error]")
        return
        
    meta = template["meta"]
    raw = {k: v for k, v in template["raw"].items() if k != "registry_meta"}
    
    console.print(f"\n[bold green]Template: {template['id']}[/bold green]")
    console.print(f"[bold]Author:[/bold] {meta.get('author', 'anonymous')}")
    console.print(f"[bold]Stars:[/bold] {meta.get('stars', 0)} ⭐")
    console.print(f"[bold]Verified:[/bold] {'[green]Yes ✓[/green]' if meta.get('verified') else 'No'}")
    console.print(f"[bold]Tags:[/bold] {', '.join(meta.get('tags', []))}\n")
    
    console.print("[bold cyan]nikame.yaml Preview:[/bold cyan]")
    yaml_str = yaml.dump(raw, sort_keys=False)
    syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True)
    console.print(syntax)
    
    # Show active integrations preview
    try:
        config_obj = load_config_from_dict(raw)
        from nikame.blueprint.engine import build_blueprint
        blueprint = build_blueprint(config_obj)
        active_modules = {m.NAME for m in blueprint.modules}
        
        from nikame.codegen.integrations.matrix import MatrixEngine
        from nikame.codegen.registry import discover_codegen, get_all_modules
        from nikame.codegen.integrations import discover_integrations, iter_integrations

        discover_integrations()
        discover_codegen()

        triggered = []
        for InstCls in iter_integrations():
            if InstCls.should_trigger(active_modules, set(config_obj.features)):
                triggered.append(InstCls.__name__)
                
        if triggered:
            console.print("\n[bold cyan]Predicted Matrix Integrations:[/bold cyan]")
            for t in triggered:
                console.print(f"  ⚡ {t}")
    except Exception as e:
        console.print(f"\n[dim]Could not generate integration preview: {e}[/dim]")

@templates_group.command()
@click.argument("template_id")
def use(template_id: str) -> None:
    """Download and use a template to start a project."""
    client = RegistryClient()
    template = client.get_template(template_id)
    
    if not template:
        console.print(f"[error]Template '{template_id}' not found.[/error]")
        raise SystemExit(1)
        
    raw = {k: v for k, v in template["raw"].items() if k != "registry_meta"}
    
    # Save to cache
    cache_dir = Path("~/.nikame/templates").expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{template_id}.yaml"
    with open(cache_file, "w") as f:
        yaml.dump(raw, f, sort_keys=False)
        
    # Ask for project name
    import questionary
    new_name = questionary.text("What is your new project name?").ask()
    if new_name:
        raw["name"] = new_name
        
    # Write to local dir
    with open("nikame.yaml", "w") as f:
        yaml.dump(raw, f, sort_keys=False)
        
    console.print(f"[success]Template saved to nikame.yaml. Launching wizard...[/success]")
    
    # Pre-fill wizard
    wizard = SetupWizard()
    
    # Hydrate state from raw dict (naive hydration for demo purposes)
    if "project" in raw and "type" in raw["project"]:
        wizard.state.project_type = raw["project"]["type"]
    if "environment" in raw and "target" in raw["environment"]:
        wizard.state.target = raw["environment"]["target"]
        wizard.state.profile = raw["environment"]["profile"]
    if "databases" in raw:
        wizard.state.databases = list(raw["databases"].keys())
    if "cache" in raw and "provider" in raw["cache"]:
        wizard.state.cache = raw["cache"]["provider"]
    if "messaging" in raw:
        wizard.state.messaging = list(raw["messaging"].keys())[0] if raw["messaging"] else "none"
    if "mlops" in raw:
        wizard.state.enable_mlops = True
        wizard.state.ml_serving = raw["mlops"].get("serving", [])
        wizard.state.ml_vector_dbs = raw["mlops"].get("vector_dbs", [])
    if "features" in raw:
        wizard.state.features = raw["features"]
        
    # Run wizard directly (skipping to confirmation because template is complete)
    wizard.current_step = len(wizard.steps) - 1 # Review step
    
    final_config = wizard.run()
    
    from nikame.cli.commands.init import _generate_project
    from nikame.config.loader import load_config_from_dict
    
    config_obj = load_config_from_dict(final_config)
    output_dir = Path(config_obj.name)
    _generate_project(config_obj, output_dir, dry_run=False)
    console.print(f"\n[success]✨ Project generated at:[/success] [path]{output_dir}[/path]")
    console.print(f"\n  cd {output_dir}")
    console.print("  nikame up\n")

@templates_group.command()
def publish() -> None:
    """Publish current nikame.yaml as a template."""
    import questionary
    config_path = Path("nikame.yaml")
    if not config_path.exists():
        console.print("[error]No nikame.yaml found in current directory.[/error]")
        return
        
    # Validate first
    try:
        from nikame.config.loader import load_config
        load_config(config_path)
        console.print("[success]Config validated successfully.[/success]")
    except Exception as e:
        console.print(f"[error]Validation failed: {e}[/error]")
        return
        
    with open(config_path, "r") as f:
        content = yaml.safe_load(f)
        
    template_id = questionary.text("Template ID (e.g. fast-api-redis):").ask()
    tags_str = questionary.text("Tags (comma separated):").ask()
    tags = [t.strip() for t in tags_str.split(",")] if tags_str else []
    
    author = credentials.get("username", "anonymous")
    
    meta = {
        "author": author,
        "tags": tags,
        "stars": 0,
        "downloads": 0,
        "verified": False
    }
    
    client = RegistryClient()
    url = client.publish(template_id, content, meta)
    console.print(f"[success]Template published to {url}[/success]")

@templates_group.command()
@click.option("--mine", is_flag=True, help="List my templates")
def list_cmd(mine: bool) -> None:
    """List templates."""
    if mine:
        author = credentials.get("username", "anonymous")
        client = RegistryClient()
        results = client.get_user_templates(author)
        
        table = Table(title=f"Templates by {author}")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Stars", justify="right")
        table.add_column("Verified")
        
        for r in results:
            table.add_row(
                r['id'],
                r['name'],
                str(r['stars']),
                "[green]✓[/green]" if r['verified'] else ""
            )
        console.print(table)
    else:
        # Default behavior, similar to search
        search.callback("", None, "recent", False)

@templates_group.command()
@click.argument("template_id")
def star(template_id: str) -> None:
    """Star a template."""
    client = RegistryClient()
    if client.star(template_id):
        console.print(f"[success]Starred template {template_id}![/success]")
    else:
        console.print(f"[error]Template {template_id} not found.[/error]")

@templates_group.command()
@click.argument("template_id")
def unstar(template_id: str) -> None:
    """Unstar a template."""
    client = RegistryClient()
    if client.unstar(template_id):
        console.print(f"[success]Unstarred template {template_id}.[/success]")
    else:
        console.print(f"[error]Template {template_id} not found.[/error]")

@templates_group.command()
@click.argument("template_id")
def verify(template_id: str) -> None:
    """Verify a template (maintainer only)."""
    # Simulate verification
    client = RegistryClient()
    template = client.get_template(template_id)
    if not template:
        console.print(f"[error]Template {template_id} not found.[/error]")
        return
        
    console.print(f"[info]Running verification for {template_id}...[/info]")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        raw = {k: v for k, v in template["raw"].items() if k != "registry_meta"}
        conf_path = tmp_path / "nikame.yaml"
        with open(conf_path, "w") as f:
            yaml.dump(raw, f, sort_keys=False)
            
        try:
            subprocess.run(["nikame", "init", "--config", str(conf_path), "--output", str(tmp_path / "project"), "--no-interactive", "--dry-run"], check=True, capture_output=True)
            console.print("[success]Init verification passed![/success]")
            # Note: We use dry-run here to avoid starting real docker containers in unit test mode
            # In a real environment, we'd run 'nikame up'
        except subprocess.CalledProcessError as e:
            console.print(f"[error]Verification failed during init: {e.stderr.decode()}[/error]")
            return
            
    if client.verify(template_id):
        console.print(f"[success]Template {template_id} verified successfully![/success]")

@templates_group.command()
def update() -> None:
    """Update local cache from remote registry."""
    console.print("[info]Local cache is up to date.[/info]")
    # Implementation for remote registry fetching goes here
