"""Interactive setup wizard for NIKAME.

Uses Questionary to prompt the user for project configuration and returns
a validated NikameConfig instance.
"""

from __future__ import annotations

from typing import Any

import questionary
from rich.table import Table
from rich.panel import Panel

from nikame.utils.logger import console


def run_wizard() -> dict[str, Any]:
    """Run the interactive wizard flow with confirmation and edit support."""
    console.print("\n[success]Welcome to the NIKAME Interactive Setup Wizard! 🚀[/success]")
    console.print("Let's define your infrastructure step by step.\n")

    # Initialize state
    state = {
        "basics": {"name": "my-app", "target": "local", "profile": "local"},
        "infra": {"databases": [], "cache": "dragonfly", "messaging": "none", "gateway": "traefik"},
        "features": {"api": "fastapi", "features": [], "generate_guide": True},
        "meta": {"type": "saas", "scale": "small", "access_pattern": "balanced"},
        "models": {},
    }

    # First pass
    state["basics"] = _get_basics(state["basics"])
    state["infra"] = _get_infrastructure()
    state["features"] = _get_features()
    state["meta"] = _get_project_meta()
    state["models"] = _get_models()

    # Confirmation/Edit Loop
    while True:
        config_dict = _assemble_config(
            state["basics"], state["infra"], state["features"], state["meta"], state["models"]
        )
        
        # Phase 3: Show Confirmation Screen
        action = _show_confirmation(config_dict)
        
        if action == "Proceed":
            return config_dict
        elif action == "Cancel":
            console.print("[warning]Generation cancelled.[/warning]")
            raise SystemExit(0)
        else:
            # Edit specific section
            section = questionary.select(
                "Which section do you want to edit?",
                choices=[
                    "Project Basics",
                    "Infrastructure",
                    "API & Features",
                    "Optimization Meta",
                    "Data Models",
                    "Back to Summary"
                ]
            ).ask()
            
            if section == "Project Basics":
                state["basics"] = _get_basics(state["basics"])
            elif section == "Infrastructure":
                state["infra"] = _get_infrastructure()
            elif section == "API & Features":
                state["features"] = _get_features()
            elif section == "Optimization Meta":
                state["meta"] = _get_project_meta()
            elif section == "Data Models":
                state["models"] = _get_models()


def _get_basics(defaults: dict[str, Any]) -> dict[str, Any]:
    """Get project name and environment."""
    name = questionary.text(
        "What is your project name?",
        default=defaults.get("name", "my-app"),
        validate=lambda x: len(x.strip()) > 0 or "Name cannot be empty",
    ).ask()

    target = questionary.select(
        "Where do you want to deploy?",
        choices=["local", "kubernetes", "aws", "gcp"],
        default=defaults.get("target", "local"),
    ).ask()

    profile = questionary.select(
        "What is the target environment profile?",
        choices=["local", "staging", "production"],
        default=defaults.get("profile", "local"),
    ).ask()

    return {"name": name, "target": target, "profile": profile}


def _get_infrastructure() -> dict[str, Any]:
    """Get database, cache, messaging, and gateway settings."""
    # Databases
    selected_db = questionary.checkbox(
        "Select databases:",
        choices=["postgres", "mongodb", "redis", "clickhouse", "qdrant", "neo4j"],
    ).ask()

    # Cache
    cache_provider = questionary.select(
        "Select a cache provider:",
        choices=["dragonfly", "redis", "none"],
        default="dragonfly",
    ).ask()

    # Messaging
    messaging_provider = questionary.select(
        "Select a messaging system:",
        choices=["redpanda", "kafka", "rabbitmq", "nats", "none"],
        default="none",
    ).ask()

    # Gateway
    gateway_provider = questionary.select(
        "Select an API gateway:",
        choices=["traefik", "nginx", "none"],
        default="traefik",
    ).ask()

    return {
        "databases": selected_db,
        "cache": cache_provider,
        "messaging": messaging_provider,
        "gateway": gateway_provider,
    }


def _get_features() -> dict[str, Any]:
    """Get high-level features and advanced components."""
    api_framework = questionary.select(
        "Which API framework are you using?",
        choices=["fastapi", "none"],
        default="fastapi",
    ).ask()

    features = questionary.checkbox(
        "Select application features:",
        choices=[
            "auth", "profiles", "file_upload", "email", 
            "payments", "background_jobs", "admin_panel", "search"
        ],
    ).ask() or []

    advanced = []
    if questionary.confirm("Add Advanced High-Fidelity Components?").ask():
        from nikame.codegen.registry import COMPONENT_REGISTRY
        choices = [
            questionary.Choice(title=f"[{info['category']}] {info['name']}", value=key)
            for key, info in COMPONENT_REGISTRY.items()
        ]
        advanced = questionary.checkbox("Select advanced components:", choices=choices).ask() or []

    return {
        "api": api_framework,
        "features": features + advanced,
        "generate_guide": questionary.confirm("Generate a project-specific GUIDE.md?", default=True).ask()
    }


def _get_project_meta() -> dict[str, Any]:
    """Get project type, scale, and access patterns."""
    console.print("\n[info]Project Metadata & Optimization[/info]")
    project_type = questionary.select(
        "What kind of project is this?",
        choices=[
            "saas", "marketplace", "content_platform", "api_service",
            "data_pipeline", "ml_platform", "internal_tool", "ecommerce"
        ],
        default="saas",
    ).ask()

    scale = questionary.select(
        "What is the expected scale?",
        choices=["small", "medium", "large"],
        default="small",
    ).ask()

    access_pattern = questionary.select(
        "What are the primary access patterns?",
        choices=["read_heavy", "write_heavy", "balanced"],
        default="balanced",
    ).ask()

    return {"type": project_type, "scale": scale, "access_pattern": access_pattern}


def _get_models() -> dict[str, Any]:
    """Phase 1: Multi-line interactive model builder."""
    console.print("\n[info]Data Model Builder[/info]")
    models = {}

    while True:
        model_name = questionary.text(
            "Enter model name (e.g. 'User', 'Post') or leave empty to finish models:",
        ).ask()
        
        if not model_name:
            break

        model_def = {"fields": {}, "relationships": {}}
        
        while True:
            field_name = questionary.text(
                f"[{model_name}] Field name (or leave empty to finish fields):"
            ).ask()
            
            if not field_name:
                break

            field_type = questionary.select(
                f"[{model_name}.{field_name}] Field type:",
                choices=["str", "int", "float", "bool", "datetime", "enum", "text", "relationship"],
                default="str",
            ).ask()

            if field_type == "relationship":
                target = questionary.text("Target model name:").ask()
                rel_type = questionary.select(
                    "Relationship type:",
                    choices=["many-to-one", "one-to-many", "many-to-many", "one-to-one"],
                    default="many-to-one"
                ).ask()
                model_def["relationships"][field_name] = {"model": target, "type": rel_type}
            elif field_type == "enum":
                values = questionary.text(
                    "Enum values (comma-separated, e.g. 'draft, published'):"
                ).ask()
                model_def["fields"][field_name] = {
                    "type": "enum",
                    "values": [v.strip() for v in values.split(",") if v.strip()]
                }
            else:
                field_config = {"type": field_type}
                field_config["required"] = questionary.confirm("Is this field required?", default=True).ask()
                field_config["unique"] = questionary.confirm("Is this field unique?", default=False).ask()
                field_config["indexed"] = questionary.confirm("Add database index?", default=False).ask()
                model_def["fields"][field_name] = field_config

        # Preview model
        _preview_model(model_name, model_def)
        models[model_name] = model_def

    return models


def _preview_model(name: str, definition: dict[str, Any]) -> None:
    """Show a rich preview of the defined model."""
    table = Table(title=f"Preview: {name}", box=None)
    table.add_column("Field", style="cyan")
    table.add_column("Details", style="magenta")

    for f_name, f_conf in definition["fields"].items():
        if isinstance(f_conf, dict):
            details = f"type: {f_conf['type']}"
            if f_conf.get("values"):
                details += f" ({', '.join(f_conf['values'])})"
            if f_conf.get("required"): details += " [bold yellow]req[/bold yellow]"
            if f_conf.get("unique"): details += " [bold green]uniq[/bold green]"
            if f_conf.get("indexed"): details += " [bold blue]idx[/bold blue]"
            table.add_row(f_name, details)
        else:
            table.add_row(f_name, f"type: {f_conf}")

    for r_name, r_conf in definition["relationships"].items():
        table.add_row(r_name, f"rel: {r_conf['type']} -> {r_conf['model']}")

    console.print(Panel(table, border_style="dim white"))


def _show_confirmation(config_dict: dict[str, Any]) -> str:
    """Show a rich summary of everything that will be generated."""
    console.clear()
    console.print(Panel("[bold green]NIKAME — Review Your Project[/bold green]", expand=False))

    # Build blueprint for "Auto-optimizations" preview
    # We do a 'pre-flight' build to show what the engine decided
    from nikame.config.loader import load_config_from_dict
    from nikame.blueprint.engine import build_blueprint
    
    try:
        config = load_config_from_dict(config_dict)
        blueprint = build_blueprint(config)
    except Exception as e:
        console.print(f"[error]Error in configuration: {e}[/error]")
        return "Edit"

    summary_table = Table(box=None, show_header=False, padding=(0, 2))
    summary_table.add_row("[key]Project[/key]", config_dict["name"])
    summary_table.add_row("[key]Type[/key]", config_dict["project"]["type"].replace("_", " ").title())
    summary_table.add_row("[key]Scale[/key]", config_dict["project"]["scale"].title())
    summary_table.add_row("[key]Target[/key]", f"{config_dict['environment']['target'].upper()} ({config_dict['environment']['profile']})")
    
    infra_list = []
    for mod in blueprint.modules:
        if mod.CATEGORY in ["database", "cache", "messaging", "gateway"]:
            infra_list.append(f"✓ {mod.NAME.title()}")
    
    summary_table.add_row("[key]Infrastructure[/key]", "\n".join(infra_list))

    # Models Summary
    models_summary = []
    for name, m_def in config_dict["models"].items():
        f_count = len(m_def["fields"])
        r_count = len(m_def["relationships"])
        models_summary.append(f"✓ {name} ({f_count} fields, {r_count} rels)")
    summary_table.add_row("[key]Models[/key]", "\n".join(models_summary) or "None")

    # Features
    features_summary = [f"✓ {f.replace('_', ' ').title()}" for f in config_dict.get("features", [])]
    summary_table.add_row("[key]Features[/key]", "\n".join(features_summary) or "None")

    # Auto-optimizations
    opts = [f"✓ {w}" for w in blueprint.warnings]
    opts.append("✓ Secure container defaults (non-root)")
    opts.append("✓ Multi-stage Docker builds")
    opts.append("✓ Healthcheck intervals tuned to scale")
    summary_table.add_row("[key]Optimizations[/key]", "\n".join(opts))

    # Estimated Cost (Phase 3)
    cost = _estimate_cost(blueprint)
    summary_table.add_row("[key]Est. Monthly Cost[/key]", f"[bold yellow]~${cost}/mo (AWS)[/bold yellow]")

    console.print(summary_table)
    console.print("\n")

    return questionary.select(
        "Proceed with generation?",
        choices=["Proceed", "Edit", "Cancel"],
        default="Proceed"
    ).ask()


def _estimate_cost(blueprint: Any) -> int:
    """Simple heuristic for monthly AWS cost estimation."""
    cost = 0
    mod_names = {m.NAME for m in blueprint.modules}
    
    # Base costs for small/medium instances
    if "postgres" in mod_names: cost += 30
    if "redpanda" in mod_names or "kafka" in mod_names: cost += 60
    if "elasticsearch" in mod_names: cost += 45
    if "mongodb" in mod_names: cost += 25
    if "redis" in mod_names or "dragonfly" in mod_names: cost += 20
    
    # Scale multiplier
    scale = blueprint.project_name # This is actually just a proxy in this mock, we should use blueprint.config.project.scale
    # Better: access internal config
    try:
        scale = getattr(blueprint, 'config', {}).project.scale
        if scale == "medium": cost *= 2.5
        elif scale == "large": cost *= 8
    except:
        pass

    return int(cost)


def _assemble_config(basics: dict, infra: dict, features: dict, meta: dict, models: dict) -> dict[str, Any]:
    """Helper to assemble the final flat config dictionary."""
    config = {
        "name": basics["name"],
        "environment": {"target": basics["target"], "profile": basics["profile"]},
        "project": {
            "type": meta["type"],
            "scale": meta["scale"],
            "access_pattern": meta["access_pattern"],
        },
        "generate_guide": features["generate_guide"],
        "models": models,
    }

    if infra["databases"]:
        config["databases"] = {db: {} for db in infra["databases"]}
    
    if infra["cache"] != "none":
        config["cache"] = {"provider": infra["cache"]}
    
    if infra["messaging"] != "none":
        config["messaging"] = {infra["messaging"]: {}}
    
    if infra["gateway"] != "none":
        config["gateway"] = {"provider": infra["gateway"]}
    
    if features["api"] != "none":
        config["api"] = {"framework": features["api"]}
    
    if features["features"]:
        config["features"] = features["features"]

    return config
