"""nikame init — Generate infrastructure from config or preset.

Loads config → validates → builds blueprint → generates files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os

import click

from nikame.blueprint.engine import Blueprint, build_blueprint
from nikame.codegen.base import CodegenContext
from nikame.codegen.ml_gateway import MLGatewayCodegen
from nikame.codegen.components.storage_service import StorageServiceCodegen
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

# ──────────────────────────── Registry Registry ────────────────────────────

# Presets removed in favor of Template Registry (Part 2)


def _generate_project(
    config: NikameConfig,
    output_dir: Path,
    *,
    dry_run: bool = False,
    no_interactive: bool = False,
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

    temp_ctx = CodegenContext(
        project_name=config.name,
        active_modules=[m.NAME for m in blueprint.modules],
        features=config.features or []
    )

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

    # Step 3: Set up file writer (buffered mode — Rules Engine validates before flush)
    writer = FileWriter(output_dir, dry_run=dry_run, buffered=not dry_run)

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


    # Step 10: Environment files
    _write_env_files(blueprint, writer)

    # Step 11: Kubernetes manifests (NEW)
    with console.status("[info]Generating Kubernetes manifests...[/info]"):
        from nikame.composers.kubernetes.manifests import generate_manifests
        manifests = generate_manifests(blueprint)
        if manifests:
            writer.write_file("infra/kubernetes/manifests.yaml", manifests)

    # Step 12: Features Codegen (NEW)
    with console.status("[info]Executing features codegen...[/info]"):
        _generate_features(config, blueprint, writer)

    # Step 13: Helm chart (NEW)
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


    # Step 13.5: Matrix Engine (Integrations Layer)
    with console.status("[info]Executing Matrix Engine integrations...[/info]"):
        from nikame.codegen.integrations.matrix import MatrixEngine
        engine = MatrixEngine(config, blueprint, writer)
        engine.execute()

    # Step 13.6: Database Migrations (Alembic)
    active_module_names = {m.NAME for m in blueprint.modules}
    if "postgres" in active_module_names:
        with console.status("[info]Generating Alembic migration scaffold...[/info]"):
            from nikame.codegen.migrations import generate_alembic_files
            db_url_env = "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB}"
            for rel_path, content in generate_alembic_files(config.name, db_url_env):
                writer.write_file(rel_path, content)

    # Step 14: Blueprint snapshot
    writer.write_blueprint(blueprint.to_dict())

    # Step 14.5: Test Skeleton
    with console.status("[info]Generating test skeleton...[/info]"):
        from nikame.codegen.test_skeleton import generate_test_files
        active_module_names_set = {m.NAME for m in blueprint.modules}
        test_files = generate_test_files(
            project_name=config.name,
            has_postgres="postgres" in active_module_names_set,
            has_redis="redis" in active_module_names_set or "dragonfly" in active_module_names_set,
            has_auth="auth" in (config.features or []),
        )
        for rel_path, content in test_files:
            writer.write_file(rel_path, content)

    # Step 14: .gitignore
    writer.write_gitignore()

    # Step 15: Project Guide (GUIDE.md)
    if config.generate_guide:
        with console.status("[info]Generating project guide (GUIDE.md)...[/info]"):
            from nikame.codegen.guide import GuideGenerator
            guide_gen = GuideGenerator(blueprint)
            guide_content = guide_gen.generate()
            writer.write_file("GUIDE.md", guide_content)

    # ━━━━━ Step 16: Auto-Wiring Engine ━━━━━
    if writer.buffered and not dry_run:
        from nikame.codegen.wiring.autowire import AutoWiringEngine
        autowire = AutoWiringEngine()
        writer.buffer, wiring_report = autowire.run(writer.buffer)

    # ━━━━━ Step 17: Rules Engine Validation ━━━━━
    if writer.buffered and not dry_run:
        from nikame.codegen.rules import RulesEngine
        rules_engine = RulesEngine()
        writer.buffer, results = rules_engine.validate(writer.buffer)

        # Check for unfixable P0 failures
        p0_failures = [
            v for r in results for v in r.violations
            if v.severity == "P0" and not v.auto_fixable
        ]
        if p0_failures:
            console.print("[bold red]Generation blocked by P0 rule violations.[/bold red]")
            for f in p0_failures:
                console.print(f"  [red]✗[/red] {f.file}: {f.message}")
            raise SystemExit(1)

        # Flush validated files to disk
        writer.flush()
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Done!
    writer.print_summary()

    # Step 17: GitHub Automation
    if not dry_run:
        _handle_github_automation(config, output_dir, no_interactive=no_interactive)

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
        
        seen_jobs = {"prometheus"}
        
        for module in blueprint.modules:
            # 1. Custom targets from module
            targets = module.prometheus_scrape_targets()
            if targets:
                for target in targets:
                    if target["job_name"] not in seen_jobs:
                        scrape_configs.append(target)
                        seen_jobs.add(target["job_name"])
            
            # 2. Default target if it looks like a Prometheus-compatible service
            # and doesn't already have custom targets defined
            elif module.NAME == "alertmanager":
                if "alertmanager" not in seen_jobs:
                    scrape_configs.append(
                        {
                            "job_name": "alertmanager",
                            "static_configs": [{"targets": ["alertmanager:9093"]}],
                        }
                    )
                    seen_jobs.add("alertmanager")
            elif module.NAME == "api":
                if "api" not in seen_jobs:
                    scrape_configs.append(
                        {
                            "job_name": "api",
                            "static_configs": [{"targets": ["api:8000"]}],
                        }
                    )
                    seen_jobs.add("api")

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
    has_grafana = any(m.NAME == "grafana" for m in blueprint.modules)
    if not has_grafana:
        return

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
        "SECRET_KEY": "Application-wide signing secret (auto-generated)",
        "CORS_ORIGINS": "CORS allowed origins (comma-separated)",
        "POSTGRES_DB": "PostgreSQL database name",
        "POSTGRES_USER": "PostgreSQL username",
        "POSTGRES_PASSWORD": "PostgreSQL password (auto-generated)",
        "JWT_SECRET_KEY": "JWT signing secret (auto-generated)",
        "REDIS_PASSWORD": "Redis/Dragonfly password (auto-generated)",
        "MINIO_ROOT_USER": "MinIO root username",
        "MINIO_ROOT_PASSWORD": "MinIO root password (auto-generated)",
        "KEYCLOAK_ADMIN": "Keycloak admin username",
        "KEYCLOAK_ADMIN_PASSWORD": "Keycloak admin password (auto-generated)",
        "GRAFANA_ADMIN_PASSWORD": "Grafana admin password (auto-generated)",
    }

    env_defaults: dict[str, str] = {
        "APP_NAME": blueprint.project_name,
        "APP_ENV": "local",
        "SECRET_KEY": "",
        "CORS_ORIGINS": "http://localhost:3000",
        "POSTGRES_DB": "app",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "",
        "JWT_SECRET_KEY": "",
        "REDIS_PASSWORD": "",
        "MINIO_ROOT_USER": "minioadmin",
        "MINIO_ROOT_PASSWORD": "",
        "KEYCLOAK_ADMIN": "admin",
        "KEYCLOAK_ADMIN_PASSWORD": "",
        "GRAFANA_ADMIN_PASSWORD": "",
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
        elif key in ("SECRET_KEY", "JWT_SECRET_KEY"):
            should_include = True
        elif key.startswith("POSTGRES") and "postgres" in active_module_names:
            should_include = True
        elif key.startswith("REDIS") and ("redis" in active_module_names or "dragonfly" in active_module_names):
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
    
    # Run explicitly requested features
    for feature_name in config.features:
        codegen_cls = get_codegen_class(feature_name)
        if not codegen_cls:
            console.print(f"[warning]Feature '{feature_name}' not found in registry. Skipping.[/warning]")
            continue

        # Check module dependencies (should already be resolved by blueprint)
        satisfied_by = {
            "redis": ["dragonfly", "valkey", "redis"],
            "kafka": ["redpanda", "kafka"]
        }
        
        missing_mods = []
        for mod_dep in codegen_cls.MODULE_DEPENDENCIES:
            if mod_dep in satisfied_by:
                if not any(sub in active_module_names for sub in satisfied_by[mod_dep]):
                    missing_mods.append(mod_dep)
            elif mod_dep not in active_module_names:
                missing_mods.append(mod_dep)

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

    # 3. Dynamic Auto-triggered Features (NEW)
    from nikame.codegen.registry import _CODEGEN_REGISTRY
    active_features = set(config.features)
    for name, cls in _CODEGEN_REGISTRY.items():
        if name in active_features: continue # Already handled
        
        if cls.should_trigger(set(active_module_names), active_features):
            console.print(f"[info]Auto-triggering component: [bold]{name}[/bold][/info]")
            codegen = cls(ctx, config)
            try:
                files = codegen.generate()
                for rel_path, content in files:
                    writer.write_file(rel_path, content)
            except Exception as exc:
                console.print(f"[warning]Failed to auto-generate '{name}': {exc}[/warning]")


def _handle_github_automation(config: NikameConfig, output_dir: Path, no_interactive: bool = False) -> None:
    """Hardened post-generation GitHub automation flow."""
    token = credentials.get_github_token()
    if not token or no_interactive:
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
@click.option(
    "--guide/--no-guide",
    default=None,
    help="Generate project-specific GUIDE.md (overrides config).",
)
@click.option(
    "--registry-mirror",
    type=str,
    default="docker.io",
    help="Container registry mirror to use (e.g. ghcr.io).",
)
@click.pass_context
def init(
    ctx: click.Context,
    config: Path | None,
    output: Path,
    dry_run: bool,
    no_interactive: bool,
    guide: bool | None,
    registry_mirror: str,
) -> None:
    """Initialize a new NIKAME project.

    Generate infrastructure files from a nikame.yaml config or
    built-in preset. Supports --dry-run for previewing output.
    """
    try:
        if config:
            console.print(f"[info]Loading config:[/info] [path]{config}[/path]")
            nikame_config = load_config(config)

            if not no_interactive:
                from nikame.cli.wizard.interactive import _show_confirmation
                action = _show_confirmation(nikame_config.model_dump())
                if action == "Cancel":
                    console.print("[warning]Generation cancelled.[/warning]")
                    raise SystemExit(0)
                elif action == "Edit":
                    from nikame.cli.wizard.interactive import run_wizard
                    config_dict = run_wizard()
                    nikame_config = load_config_from_dict(config_dict)
        elif not no_interactive:
            # Launch wizard
            from nikame.cli.wizard.interactive import run_wizard
            config_dict = run_wizard()
            nikame_config = load_config_from_dict(config_dict)
        else:
            console.print("[error]No config provided and --no-interactive set. Use --config or launch without --no-interactive.[/error]")
            raise SystemExit(1)

        # CLI overrides
        if guide is not None:
            nikame_config.generate_guide = guide
        if registry_mirror != "docker.io":
            nikame_config.registry.mirror = registry_mirror

        # Override output name if using preset
        output_dir = output / nikame_config.name if output == Path(".") else output

        if nikame_config.api:
            console.print(f"[debug]API Framework: {nikame_config.api.framework}[/debug]")
        else:
            console.print("[error]No API found in config object[/error]")
        _generate_project(nikame_config, output_dir, dry_run=dry_run, no_interactive=no_interactive)

        console.print(f"\n[success]✨ Project generated at:[/success] [path]{output_dir}[/path]")
        console.print(f"\n  cd {output_dir}")
        console.print("  nikame up\n")

    except NikameError as exc:
        console.print(f"\n[error]✗ {exc.message}[/error]")
        raise SystemExit(1) from exc
