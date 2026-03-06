"""nikame init — Generate infrastructure from config or preset.

Loads config → validates → builds blueprint → generates files.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import click

from nikame.blueprint.engine import Blueprint, build_blueprint
from nikame.codegen.base import CodegenContext
from nikame.codegen.ml_gateway import MLGatewayCodegen
from nikame.codegen.registry import (
    COMPONENT_REGISTRY,
    discover_codegen,
    get_codegen_class,
)
from nikame.codegen.schema_codegen import SchemaCodegen
from nikame.composers.docker_compose import generate_compose
from nikame.config.loader import load_config, load_config_from_dict
from nikame.config.schema import NikameConfig
from nikame.config.validator import validate_config
from nikame.exceptions import NikameError, NikameGenerationError
from nikame.utils.auth import credentials
from nikame.utils.file_writer import FileWriter
from nikame.utils.git import (
    git_add_remote,
    git_commit,
    git_init,
    git_push,
    save_project_metadata,
)
from nikame.utils.github_client import GitHubClient
from nikame.utils.logger import console

# ──────────────────────────── Presets ────────────────────────────

PRESETS: dict[str, dict[str, Any]] = {
    "saas-starter": {
        "name": "saas-starter",
        "version": "1.0",
        "description": "Production SaaS — FastAPI + Postgres + Redis + Keycloak + Stripe",
        "environment": {"target": "local", "profile": "local"},
        "api": {"framework": "fastapi", "workers": "auto"},
        "databases": {"postgres": {"version": "16", "pgbouncer": True}},
        "cache": {"provider": "redis"},
        "auth": {"provider": "keycloak"},
        "ci_cd": {"github_actions": True},
        "features": ["auth", "stripe", "rate_limiting", "health_check"],
    },
    "mlops-rag": {
        "name": "mlops-rag",
        "version": "1.0",
        "description": "MLOps RAG Stack — vLLM + Qdrant + Unstructured + Celery",
        "environment": {"target": "local", "profile": "local"},
        "api": {"framework": "fastapi"},
        "databases": {"qdrant": {}},
        "mlops": {
            "models": [
                {"name": "llm", "source": "huggingface", "model": "mistralai/Mistral-7B-v0.1", "serve_with": "vllm"}
            ]
        },
        "ci_cd": {"github_actions": True},
        "features": ["vector_search", "cron_jobs"],
    },
    "realtime-analytics": {
        "name": "realtime-analytics",
        "version": "1.0",
        "description": "Real-time Analytics — RedPanda + ClickHouse + Grafana",
        "environment": {"target": "local", "profile": "local"},
        "messaging": {
            "redpanda": {"brokers": 1, "topics": [{"name": "events", "partitions": 3}]}
        },
        "databases": {"clickhouse": {}},
        "observability": {"stack": "full"},
        "ci_cd": {"github_actions": True},
        "features": ["pubsub"],
    },
    "api-gateway": {
        "name": "api-gateway",
        "version": "1.0",
        "description": "Hardened API Gateway — Traefik + Let's Encrypt + OTel",
        "environment": {"target": "local", "profile": "local"},
        "gateway": {"provider": "traefik", "tls": {"enabled": True, "provider": "letsencrypt"}},
        "api": {"tracing": {"enabled": True, "provider": "otel"}},
        "ci_cd": {"github_actions": True},
        "features": ["rate_limiting"],
    },
    "multi-tenant": {
        "name": "multi-tenant",
        "version": "1.0",
        "description": "Multi-tenant K8s — Namespace Isolation + Sealed Secrets",
        "environment": {"target": "kubernetes", "profile": "production", "namespace": "isolated"},
        "security": {"secrets": {"provider": "sealed-secrets"}, "network_policy": {"provider": "cilium"}},
        "ci_cd": {"github_actions": True},
        "features": ["multi_tenancy"],
    },
}


def _generate_project(
    config: NikameConfig,
    output_dir: Path,
    *,
    dry_run: bool = False,
) -> None:
    """Run the full generation pipeline.

    1. Validate cross-module constraints
    2. Build the blueprint (resolve dependencies)
    3. Generate Docker Compose output
    4. Generate Prometheus/Grafana configs
    5. Write all files

    Args:
        config: Validated NikameConfig.
        output_dir: Where to write generated files.
        dry_run: Preview without writing.
    """
    console.print(f"\n[key]Project:[/key] {config.name}")
    console.print(f"[key]Target:[/key] {config.environment.target}")
    console.print(f"[key]Profile:[/key] {config.environment.profile}")
    console.print()

    # Step 1: Cross-module validation
    with console.status("[info]Validating configuration...[/info]"):
        warnings = validate_config(config)

    # Step 2: Build blueprint
    with console.status("[info]Resolving module dependencies...[/info]"):
        blueprint = build_blueprint(config)

    # Step 2.5: Collect component wiring (imports, routers, etc.)
    # This must happen BEFORE scaffolding so the API module can use it.
    discover_codegen()
    for feature_name in config.features:
        # Check both registries (features and components)
        codegen_cls = get_codegen_class(feature_name)
        if codegen_cls:
            # Create a temporary context for wiring extraction
            # Requirements and wiring are static-ish or only depend on basic ctx
            temp_ctx = CodegenContext(
                project_name=config.name,
                active_modules=[m.NAME for m in blueprint.modules],
                features=config.features
            )
            try:
                generator = codegen_cls(temp_ctx, config)
                w = generator.wiring()
                if w and blueprint.modules:
                    # Inject wiring into the shared ModuleContext
                    # All modules share the same ctx instance
                    blueprint.modules[0].ctx.wiring[feature_name] = w
            except Exception as exc:
                console.print(f"[warning]⚠ Could not extract wiring for '{feature_name}': {exc}[/warning]")

    # Step 3: Set up file writer
    writer = FileWriter(output_dir, dry_run=dry_run)

    # Step 4: Write nikame.yaml (copy config)
    writer.write_yaml("nikame.yaml", config.model_dump())

    # Step 5: Docker Compose
    with console.status("[info]Generating Docker Compose...[/info]"):
        compose = generate_compose(blueprint)
        writer.write_yaml("infra/docker-compose.yml", compose)

    # Step 6: Prometheus configs
    _write_prometheus_configs(blueprint, writer)

    # Step 7: Grafana configs
    _write_grafana_configs(blueprint, writer)

    # Step 8: Init scripts
    _write_init_scripts(blueprint, writer)

    # Step 9: Application scaffolding (NEW)
    with console.status("[info]Generating application scaffolding...[/info]"):
        _write_scaffolding(blueprint, writer)

    # Step 10: ML Gateway (NEW)
    if config.mlops:
        with console.status("[info]Generating ML Gateway...[/info]"):
            MLGatewayCodegen(config).generate(output_dir)

    # Step 11: Schema-Driven Codegen (NEW)
    if config.models:
        with console.status("[info]Generating Data Models and CRUD endpoints...[/info]"):
            SchemaCodegen(config).generate(output_dir)

    # Step 12: Advanced Components (NEW)
    
    ctx = CodegenContext(
        project_name=config.name,
        active_modules=[m.NAME for m in blueprint.modules],
        features=config.features
    )
    

    for comp_key in config.features:
        comp_info = COMPONENT_REGISTRY.get(comp_key)
        if comp_info and "class" in comp_info:
            with console.status(f"[info]Generating {comp_info['name']}...[/info]"):
                generator = comp_info["class"](ctx, config)
                files = generator.generate()
                # Ensure the app directory exists as a package
                writer.write_file("app/__init__.py", "")
                
                for path, content in files:
                    # Redirect 'app/' to 'app/' for unified build context
                    if path.startswith("app/"):
                        target_path = path
                    else:
                        target_path = path
                    writer.write_file(target_path, content)

    # Step 10: Environment files
    _write_env_files(blueprint, writer)

    # Step 11: Kubernetes manifests (NEW)
    with console.status("[info]Generating Kubernetes manifests...[/info]"):
        from nikame.composers.kubernetes.manifests import generate_manifests
        manifests = generate_manifests(blueprint)
        if manifests:
            writer.write_file("infra/kubernetes/manifests.yaml", manifests)

    # Step 12: Helm chart (NEW)
    with console.status("[info]Generating Helm chart...[/info]"):
        from nikame.composers.kubernetes.helm import generate_helm_chart
        helm_files = generate_helm_chart(blueprint)
        for rel_path, content in helm_files.items():
            writer.write_file(f"infra/helm/{rel_path}", content)

    # Step 13: Terraform (NEW)
    if config.environment.target in ["aws", "gcp", "azure"]:
        with console.status(f"[info]Generating Terraform for {config.environment.target}...[/info]"):
            from nikame.composers.terraform import generate_terraform
            tf_files = generate_terraform(blueprint)
            for rel_path, content in tf_files.items():
                writer.write_file(f"infra/terraform/{rel_path}", content)

    # Step 13: Codegen features (NEW)
    if config.features:
        with console.status("[info]Generating application features...[/info]"):
            _generate_features(config, blueprint, writer)

    # Step 14: Blueprint snapshot
    writer.write_blueprint(blueprint.to_dict())

    # Step 14: .gitignore
    writer.write_gitignore()

    # Done!
    writer.print_summary()

    # Step 15: GitHub Automation (NEW)
    if not dry_run:
        _handle_github_automation(config, output_dir)

    if blueprint.warnings:
        console.print("\n[warning]⚠ Optimization suggestions:[/warning]")
        for w in blueprint.warnings:
            console.print(f"  {w}")


def _write_prometheus_configs(
    blueprint: Blueprint, writer: FileWriter
) -> None:
    """Write per-module Prometheus alert rules."""
    all_rules: list[dict[str, Any]] = []
    for module in blueprint.modules:
        rules = module.prometheus_rules()
        if rules:
            all_rules.extend(rules)

    if all_rules:
        rules_yaml: dict[str, Any] = {
            "groups": [
                {
                    "name": "nikame-alerts",
                    "rules": all_rules,
                }
            ]
        }
        writer.write_yaml("infra/configs/prometheus/rules/nikame_alerts.yml", rules_yaml)

        # Also write a basic prometheus.yml
        scrape_configs: list[dict[str, Any]] = [
            {
                "job_name": "prometheus",
                "static_configs": [{"targets": ["localhost:9090"]}],
            },
        ]
        for module in blueprint.modules:
            # 1. Custom targets from module
            targets = module.prometheus_scrape_targets()
            if targets:
                scrape_configs.extend(targets)
            
            # 2. Default target if it looks like a Prometheus-compatible service
            # and doesn't already have custom targets defined
            elif module.NAME in ["prometheus", "alertmanager"]:
                scrape_configs.append(
                    {
                        "job_name": module.NAME,
                        "static_configs": [{"targets": [f"{module.NAME}:9090"]}],
                    }
                )
            elif module.NAME == "api":
                scrape_configs.append(
                    {
                        "job_name": "api",
                        "static_configs": [{"targets": ["api:8000"]}],
                    }
                )

        prom_config: dict[str, Any] = {
            "global": {
                "scrape_interval": "15s",
                "evaluation_interval": "15s",
            },
            "rule_files": ["/etc/prometheus/rules/*.yml"],
            "alerting": {
                "alertmanagers": [
                    {"static_configs": [{"targets": ["alertmanager:9093"]}]}
                ]
            },
            "scrape_configs": scrape_configs,
        }
        writer.write_yaml("infra/configs/prometheus/prometheus.yml", prom_config)

        # Basic alertmanager config
        alertmanager_config = {
            "global": {"resolve_timeout": "5m"},
            "route": {
                "group_by": ["alertname"],
                "group_wait": "10s",
                "group_interval": "10s",
                "repeat_interval": "1h",
                "receiver": "default",
            },
            "receivers": [{"name": "default"}],
        }
        writer.write_yaml("infra/configs/prometheus/alertmanager.yml", alertmanager_config)


def _write_grafana_configs(
    blueprint: Blueprint, writer: FileWriter
) -> None:
    """Write Grafana provisioning and per-module dashboards."""
    for module in blueprint.modules:
        # Init scripts (provisioning configs)
        for filename, content in module.init_scripts():
            if filename.startswith("provisioning/"):
                writer.write_file(f"infra/configs/grafana/{filename}", content)

        # Dashboard JSON
        dashboard = module.grafana_dashboard()
        if dashboard:
            dashboard_json = json.dumps(dashboard, indent=2)
            writer.write_file(
                f"infra/configs/grafana/dashboards/{module.NAME}_dashboard.json",
                dashboard_json,
            )


def _write_init_scripts(
    blueprint: Blueprint, writer: FileWriter
) -> None:
    """Write module init scripts (SQL, shell, etc.)."""
    for module in blueprint.modules:
        for filename, content in module.init_scripts():
            if not filename.startswith("provisioning/"):
                writer.write_file(
                    f"infra/configs/{module.NAME}/{filename}", content
                )


def _write_scaffolding(
    blueprint: Blueprint, writer: FileWriter
) -> None:
    """Write application scaffold files (source code, Dockerfiles, etc.)."""
    for module in blueprint.modules:
        for rel_path, content in module.scaffold_files():
            writer.write_file(rel_path, content)


def _write_env_files(
    blueprint: Blueprint, writer: FileWriter
) -> None:
    """Generate .env.example and .env.generated files."""
    env_descriptions: dict[str, str] = {
        "APP_NAME": "Application name",
        "APP_ENV": "Application environment (local/staging/production)",
        "CORS_ORIGINS": "CORS allowed origins (comma-separated)",
        "POSTGRES_DB": "PostgreSQL database name",
        "POSTGRES_USER": "PostgreSQL username",
        "POSTGRES_PASSWORD": "PostgreSQL password (auto-generated)",
        "MINIO_ROOT_USER": "MinIO root username",
        "MINIO_ROOT_PASSWORD": "MinIO root password (auto-generated)",
        "KEYCLOAK_ADMIN": "Keycloak admin username",
        "KEYCLOAK_ADMIN_PASSWORD": "Keycloak admin password (auto-generated)",
        "GRAFANA_ADMIN_PASSWORD": "Grafana admin password (auto-generated)",
    }

    env_defaults: dict[str, str] = {
        "APP_NAME": blueprint.project_name,
        "APP_ENV": "local",
        "CORS_ORIGINS": "*",
        "POSTGRES_DB": "app",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "",
        "MINIO_ROOT_USER": "minioadmin",
        "MINIO_ROOT_PASSWORD": "",
        "KEYCLOAK_ADMIN": "admin",
        "KEYCLOAK_ADMIN_PASSWORD": "",
        "GRAFANA_ADMIN_PASSWORD": "admin",
    }

    # Only include env vars for active modules
    active_env_desc: dict[str, str] = {}
    active_env_defaults: dict[str, str] = {}
    active_module_names = {m.NAME for m in blueprint.modules}

    for key, desc in env_descriptions.items():
        # Include postgres vars if postgres is active, etc.
        should_include = False
        if key.startswith("APP") or key == "CORS_ORIGINS":
            should_include = True
        elif key.startswith("POSTGRES") and "postgres" in active_module_names:
            should_include = True
        elif key.startswith("MINIO") and "minio" in active_module_names:
            should_include = True
        elif key.startswith("KEYCLOAK") and "keycloak" in active_module_names:
            should_include = True
        elif key.startswith("GRAFANA") and "grafana" in active_module_names:
            should_include = True

        if should_include:
            active_env_desc[key] = desc
            active_env_defaults[key] = env_defaults[key]

    if active_env_desc:
        writer.write_env_example(active_env_desc)
        writer.write_env_generated(active_env_defaults)


def _generate_features(
    config: NikameConfig,
    blueprint: Blueprint,
    writer: FileWriter,
) -> None:
    """Instantiate and run codegen features."""
    # 1. Prepare context
    active_module_names = [m.NAME for m in blueprint.modules]

    # Extract connection strings if available
    db_url = ""
    cache_url = ""
    for module in blueprint.modules:
        env = module.env_vars()
        if "DATABASE_URL" in env and not db_url:
            db_url = env["DATABASE_URL"]
        if "REDIS_URL" in env and not cache_url:
            cache_url = env["REDIS_URL"]

    ctx = CodegenContext(
        project_name=config.name,
        active_modules=active_module_names,
        database_url=db_url,
        cache_url=cache_url,
        features=config.features,
    )

    # 2. Discover and run features
    discover_codegen()

    for feature_name in config.features:
        codegen_cls = get_codegen_class(feature_name)
        if not codegen_cls:
            console.print(f"[warning]Feature '{feature_name}' not found in registry. Skipping.[/warning]")
            continue

        # Check module dependencies (should already be resolved by blueprint)
        missing_mods = [m for m in codegen_cls.MODULE_DEPENDENCIES if m not in active_module_names]
        if missing_mods:
            console.print(f"[error]Feature '{feature_name}' requires modules {missing_mods} which are missing even after blueprint resolution.[/error]")
            continue

        codegen = codegen_cls(ctx, config)
        try:
            files = codegen.generate()
            for rel_path, content in files:
                writer.write_file(rel_path, content)
        except Exception as exc:
            raise NikameGenerationError(f"Failed to generate feature '{feature_name}': {exc}") from exc


def _handle_github_automation(config: NikameConfig, output_dir: Path) -> None:
    """Hardened post-generation GitHub automation flow."""
    token = credentials.get_github_token()
    if not token:
        return

    import anyio
    import questionary

    from nikame.cli.commands.github import _sync_secrets_logic

    console.print(f"\n[key]GitHub Integration Detected ({credentials.get_github_user().get('login')})[/key]")

    # 1. Main Choice
    choice = questionary.select(
        "What would you like to do with GitHub?",
        choices=[
            "Create new repository and push",
            "Push to existing repository",
            "Set custom remote only (no push)",
            "Skip GitHub for now",
        ],
        default="Create new repository and push",
    ).ask()

    if choice == "Skip GitHub for now":
        return

    client = GitHubClient(token)
    owner = credentials.get_github_user().get("login")
    repo_name = config.name
    repo_url = ""

    # 2. Detail Gathering
    if choice == "Create new repository and push":
        # Check orgs
        try:
            orgs = anyio.run(client.get_user_orgs)
            target = "Personal"
            if orgs:
                target = questionary.select(
                    "Where to create the repository?",
                    choices=["Personal"] + [o["login"] for o in orgs],
                    default="Personal",
                ).ask()

            owner = credentials.get_github_user().get("login") if target == "Personal" else target
            private = questionary.confirm("Make repository private?", default=True).ask()

            with console.status(f"[info]Creating repo {owner}/{repo_name}...[/info]"):
                created = anyio.run(client.create_repo, repo_name, config.description, private, None if target == "Personal" else target)
                repo_url = created["clone_url"]
                console.print(f"[success]✓ Repository created:[/success] {repo_url}")
        except Exception as e:
            console.print(f"[error]Failed to create repo: {e}[/error]")
            return

    elif choice == "Push to existing repository" or choice == "Set custom remote only (no push)":
        repo_url = questionary.text("Enter remote URL (GitHub, GitLab, SSH, etc.):").ask()
        if not repo_url:
            return
        # Try to parse owner/repo from URL if it's GitHub
        if "github.com" in repo_url:
            parts = repo_url.rstrip("/").split("/")
            if len(parts) >= 2:
                repo_name = parts[-1].replace(".git", "")
                owner = parts[-2]

    # 3. Execution
    try:
        git_init(output_dir)
        git_add_remote(output_dir, "origin", repo_url)

        # Metadata persistence
        metadata = {
            "remote_url": repo_url,
            "github_owner": owner,
            "github_repo": repo_name,
            "platform": "github" if "github.com" in repo_url else "custom",
        }
        save_project_metadata(output_dir, metadata)

        if choice != "Set custom remote only (no push)":
            git_commit(output_dir, "Initial commit by NIKAME")
            git_push(output_dir, remote="origin", branch="main")
            console.print("[success]✓ Project pushed to remote.[/success]")

            # 4. CI/CD & Secrets (only for GitHub)
            if "github.com" in repo_url:
                if questionary.confirm("Set up GitHub Actions workflow?", default=True).ask():
                    _generate_github_actions(output_dir)

                if questionary.confirm("Synchronize secrets to GitHub?", default=True).ask():
                    # Need to change directory to call sync logic correctly or pass path
                    os.chdir(output_dir)
                    _sync_secrets_logic(owner, repo_name, token)

    except Exception as e:
        console.print(f"[error]Automation failed: {e}[/error]")


def _generate_github_actions(output_dir: Path) -> None:
    """Internal helper to write the production-grade CI template."""
    workflow_dir = output_dir / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)

    # In a real scenario, we'd use the Template engine
    template_path = Path(__file__).parent.parent.parent / "templates" / "ci_cd" / "github_actions" / "ci.yml.j2"
    if template_path.exists():
        content = template_path.read_text()
        (workflow_dir / "ci.yml").write_text(content)
        console.print("[success]✓ CI workflow created at .github/workflows/ci.yml[/success]")


# ──────────────────────────── CLI Command ────────────────────────────


@click.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to nikame.yaml config file.",
)
@click.option(
    "--preset", "-p",
    type=click.Choice(list(PRESETS.keys())),
    default=None,
    help="Use a built-in preset (saas-starter, minimal).",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=Path("."),
    help="Output directory for generated files.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without writing files.",
)
@click.option(
    "--no-interactive",
    is_flag=True,
    default=False,
    help="Skip interactive wizard.",
)
@click.pass_context
def init(
    ctx: click.Context,
    config: Path | None,
    preset: str | None,
    output: Path,
    dry_run: bool,
    no_interactive: bool,
) -> None:
    """Initialize a new NIKAME project.

    Generate infrastructure files from a nikame.yaml config or
    built-in preset. Supports --dry-run for previewing output.
    """
    try:
        if config and preset:
            console.print("[error]Cannot use both --config and --preset[/error]")
            raise SystemExit(1)

        if preset:
            console.print(f"[info]Using preset:[/info] [module]{preset}[/module]")
            nikame_config = load_config_from_dict(PRESETS[preset])
        elif config:
            console.print(f"[info]Loading config:[/info] [path]{config}[/path]")
            nikame_config = load_config(config)
        elif not no_interactive:
            # Launch wizard
            from nikame.cli.wizard import run_wizard
            config_dict = run_wizard()
            nikame_config = load_config_from_dict(config_dict)
        else:
            # Default to saas-starter if no-interactive is set but no config provided
            console.print("[info]No config/preset and --no-interactive set, using saas-starter[/info]")
            nikame_config = load_config_from_dict(PRESETS["saas-starter"])

        # Override output name if using preset
        output_dir = output / nikame_config.name if output == Path(".") else output

        console.print("\n[success]🚀 NIKAME init[/success]\n")
        _generate_project(nikame_config, output_dir, dry_run=dry_run)

        console.print(f"\n[success]✨ Project generated at:[/success] [path]{output_dir}[/path]")
        console.print(f"\n  cd {output_dir}")
        console.print("  nikame up\n")

    except NikameError as exc:
        console.print(f"\n[error]✗ {exc.message}[/error]")
        raise SystemExit(1) from exc
