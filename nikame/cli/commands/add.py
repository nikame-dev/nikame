from pathlib import Path

import typer
from rich.prompt import Confirm

from nikame.cli.output import (
    console,
    print_header,
    print_section,
    print_success,
)
from nikame.core.registry.loader import RegistryLoader
from nikame.engines.scaffold import ScaffoldEngine

app = typer.Typer(help="Add a pattern to the project.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    pattern_id: str = typer.Argument(..., help="ID of the pattern to add (e.g. auth.jwt)"),
    registry_path: Path = typer.Option(Path("registry"), "--registry", help="Path to pattern registry"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview changes without applying"),
    no_confirm: bool = typer.Option(False, "--no-confirm", "-y", help="Skip confirmation prompt")
) -> None:
    if ctx.invoked_subcommand is not None:
        return
        
    print_header(f"Add Pattern: {pattern_id}")
    
    loader = RegistryLoader(registry_path)
    pattern = loader.load_pattern(pattern_id)
    
    if not pattern:
        console.print(f"[danger]Error:[/] Pattern [accent]{pattern_id}[/] not found in registry.")
        raise typer.Exit(code=1)
        
    # 1. Show Pattern Summary (ui_ux.md 4.2)
    console.print(f"[bold accent]{pattern.display_name}[/] [text_muted]v{pattern.version}[/]")
    console.print(f"[text_primary]{pattern.description}[/]\n")
    
    console.print(f"Dependencies   {' '.join(pattern.requires) if pattern.requires else '[text_muted]none[/]'}")
    console.print(f"Conflicts      {' '.join(pattern.conflicts) if pattern.conflicts else '[text_muted]none[/]'}")
    console.print("Risk           [warning]MEDIUM[/]\n")
    
    # 2. Show Files to Create/Modify
    if pattern.injects:
        print_section("Proposed Changes")
        for inj in pattern.injects:
            color = "success" if inj.operation == "create" else "warning"
            symbol = "+" if inj.operation == "create" else "~"
            console.print(f"  [{color}]{symbol}[/] [text_primary]{inj.path}[/] [text_muted]({inj.operation})[/]")
            
    # 3. Show Env Vars
    if pattern.env_vars:
        print_section("Environment Variables")
        for ev in pattern.env_vars:
            console.print(f"  [accent]{ev.name}[/] [text_muted](default: {ev.default})[/]")
            
    console.print("\n")
    
    # 4. Confirmation
    if not no_confirm:
        if not Confirm.ask("Apply these changes?", default=True):
            console.print("[warning]Operation cancelled.[/]")
            return
            
    if dry_run:
        print_success("Dry run completed. No files changed.")
        return
        
    # 5. Execute
    scaffolder = ScaffoldEngine()
    
    # In a real scenario, we'd gather context from .env or prompts
    # For now, we'll use empty context or defaults
    context = {ev.name: ev.default for ev in pattern.env_vars}
    
    project_root = Path.cwd()
    
    for inj in pattern.injects:
        target_path = project_root / inj.path
        
        if inj.operation == "create":
            # For Phase 4, we'll read the template file from the registry
            if inj.template:
                template_path = registry_path / "patterns" / pattern_id.replace(".", "/") / "templates" / inj.template
                if template_path.exists():
                    content = scaffolder.render_template(template_path.read_text(), context)
                    scaffolder.write_file(target_path, content, overwrite=True)
                
        elif inj.operation == "inject":
            content = inj.content or ""
            if inj.template:
                template_path = registry_path / "patterns" / pattern_id.replace(".", "/") / "templates" / inj.template
                if template_path.exists():
                    content = scaffolder.render_template(template_path.read_text(), context)
            
            if inj.marker:
                scaffolder.inject_into_file(target_path, inj.marker, content)

    print_success(f"Pattern [accent]{pattern_id}[/] added successfully!")
    console.print("Run `[accent]nikame verify[/]` to ensure system integrity.")
