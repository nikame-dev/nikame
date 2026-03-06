"""Interactive setup wizard for NIKAME.

Uses Questionary to prompt the user for project configuration and returns
a validated NikameConfig instance.
"""

from __future__ import annotations

from typing import Any

import questionary

from nikame.utils.logger import console


def run_wizard() -> dict[str, Any]:
    """Run the interactive wizard flow.

    Returns:
        A dictionary representation of NikameConfig.
    """
    console.print("[success]Welcome to the NIKAME Interactive Setup Wizard! 🚀[/success]")
    console.print("Let's define your infrastructure step by step.\n")

    # 1. Basics
    name = questionary.text(
        "What is your project name?",
        default="my-app",
        validate=lambda x: len(x.strip()) > 0 or "Name cannot be empty",
    ).ask()

    # 2. Environment
    target = questionary.select(
        "Where do you want to deploy?",
        choices=["local", "kubernetes", "aws", "gcp"],
        default="local",
    ).ask()

    profile = questionary.select(
        "What is the target environment profile?",
        choices=["local", "staging", "production"],
        default="local",
    ).ask()

    # 3. API
    api_framework = questionary.select(
        "Which API framework are you using?",
        choices=["fastapi", "none"],
        default="fastapi",
    ).ask()

    api_config = None
    if api_framework != "none":
        api_config = {"framework": api_framework}

    # 4. Databases
    selected_db = questionary.checkbox(
        "Select databases:",
        choices=[
            "postgres",
            "mongodb",
            "redis",
            "clickhouse",
            "qdrant",
            "neo4j",
        ],
    ).ask()

    databases_config = {}
    for db in selected_db:
        databases_config[db] = {}

    # 5. Cache
    cache_provider = questionary.select(
        "Select a cache provider:",
        choices=["dragonfly", "redis", "none"],
        default="dragonfly",
    ).ask()

    cache_config = None
    if cache_provider != "none":
        cache_config = {"provider": cache_provider}

    # 6. Messaging
    messaging_provider = questionary.select(
        "Select a messaging system:",
        choices=["redpanda", "kafka", "rabbitmq", "nats", "none"],
        default="none",
    ).ask()

    messaging_config = {}
    if messaging_provider != "none":
        messaging_config[messaging_provider] = {}

    # 7. Gateway
    gateway_provider = questionary.select(
        "Select an API gateway:",
        choices=["traefik", "nginx", "none"],
        default="traefik",
    ).ask()

    gateway_config = None
    if gateway_provider != "none":
        gateway_config = {"provider": gateway_provider}

    # 8. Observability
    obs_stack = questionary.select(
        "Select observability stack:",
        choices=["full", "lightweight", "none"],
        default="full",
    ).ask()

    observability_config = {"stack": obs_stack}

    # 9. CI/CD
    selected_cicd = questionary.checkbox(
        "Select CI/CD tools:",
        choices=["gitea", "woodpecker", "argocd"],
    ).ask()

    cicd_config = {}
    for tool in selected_cicd:
        cicd_config[tool] = True

    # 10. Features (Codegen)
    selected_features = questionary.checkbox(
        "Select application features:",
        choices=[
            "auth",
            "profiles",
            "file_upload",
            "email",
            "payments",
            "background_jobs",
            "admin_panel",
            "search",
        ],
    ).ask() or []

    # 11. Advanced High-Fidelity Components (NEW)
    selected_advanced = []
    if questionary.confirm("Would you like to add Advanced High-Fidelity Components?").ask():
        from nikame.codegen.registry import COMPONENT_REGISTRY
        choices = [
            questionary.Choice(
                title=f"[{info['category']}] {info['name']}",
                value=key
            ) for key, info in COMPONENT_REGISTRY.items()
        ]
        selected_advanced = questionary.checkbox(
            "Select advanced components:",
            choices=choices
        ).ask() or []

    selected_features.extend(selected_advanced)

    # 12. Guide
    generate_guide = questionary.confirm(
        "Generate a project-specific GUIDE.md?", default=True
    ).ask()

    # Assemble
    config_dict = {
        "name": name,
        "environment": {"target": target, "profile": profile},
        "generate_guide": generate_guide,
    }
    if api_config:
        config_dict["api"] = api_config
    if databases_config:
        config_dict["databases"] = databases_config
    if cache_config:
        config_dict["cache"] = cache_config
    if messaging_config:
        config_dict["messaging"] = messaging_config
    if gateway_config:
        config_dict["gateway"] = gateway_config
    if observability_config:
        config_dict["observability"] = observability_config
    if cicd_config:
        config_dict["ci_cd"] = cicd_config
    if selected_features:
        config_dict["features"] = [f.lower().replace(" ", "_") for f in selected_features]

    return config_dict
