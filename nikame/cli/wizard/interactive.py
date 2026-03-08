from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nikame.config.loader import load_config_from_dict
from nikame.utils.logger import console

# ──────────────────────────── Constants & Types ────────────────────────────

# Project types removed - detection is now feature-based

@dataclass
class WizardState:
    """Manages wizard state, validation, and cascading invalidation."""
    
    # 1. Project Basics
    name: str = "my-app"
    target: Literal["local", "kubernetes", "aws", "gcp"] = "local"
    profile: Literal["local", "staging", "production"] = "local"
    scale: str = "small"
    access_pattern: str = "balanced"
    
    # 2. Infrastructure
    databases: list[str] = field(default_factory=list)
    cache: str = "dragonfly"
    messaging: str = "none"
    gateway: str = "traefik"
    observability: str = "none"
    ci_cd: list[str] = field(default_factory=list)
    
    # 2.1 Contextual Infra Follow-ups
    pg_replicas: int = 1
    msg_mps: str = "under 1k" # messages per second
    msg_partitions: int = 3
    auth_pattern: str = "JWT stateless"
    storage_buckets: list[str] = field(default_factory=list)
    alert_channels: list[str] = field(default_factory=list)
    cloud_provider: str = "bare-metal"
    
    # 3. Features & Components
    api_framework: str = "fastapi"
    features: list[str] = field(default_factory=list)
    generate_guide: bool = True
    
    # 3.1 Advanced Feature Follow-ups
    tenancy_model: str = "separate schemas"
    max_rps: int = 100
    
    # 4. MLOps (Optional)
    enable_mlops: bool = False
    ml_serving: list[str] = field(default_factory=list)
    ml_tracking: list[str] = field(default_factory=list)
    ml_orchestration: list[str] = field(default_factory=list)
    ml_monitoring: list[str] = field(default_factory=list)
    ml_vector_dbs: list[str] = field(default_factory=list)
    ml_agents: list[str] = field(default_factory=list)
    ml_caching: list[str] = field(default_factory=list)
    
    # 4.1 MLOps Follow-ups
    ml_training_enabled: bool = False
    ml_orchestrator: str = "prefect"
    ml_embedding_dim: int = 1536
    
    # 5. Data Models
    models: dict[str, Any] = field(default_factory=dict)
    
    # Tracking dirty steps for cascading invalidation
    completed_steps: set[int] = field(default_factory=set)
    
    # Auto-add tracking for confirmation screen
    auto_added_modules: set[str] = field(default_factory=set)

    def to_config_dict(self) -> dict[str, Any]:
        """Assembles the actual NikameConfig dictionary."""
        config = {
            "name": self.name,
            "environment": {"target": self.target, "profile": self.profile},
            "project": {
                "scale": self.scale,
                "access_pattern": self.access_pattern,
            },
            "generate_guide": self.generate_guide,
            "models": self.models,
            "_auto_added": self.auto_added_modules,
        }

        # Mapping follow-ups to config
        if self.target == "kubernetes":
            cloud_map = {
                "AWS EKS": "aws",
                "GCP GKE": "gcp",
                "Azure AKS": "azure",
            }
            config["environment"]["cloud"] = cloud_map.get(self.cloud_provider)

        # Infra
        if self.databases:
            config["databases"] = {}
            for db in self.databases:
                db_conf = {}
                if db == "postgres":
                    db_conf["replicas"] = self.pg_replicas
                config["databases"][db] = db_conf

        if self.cache != "none":
            config["cache"] = {"provider": self.cache}
        
        if self.messaging != "none":
            mps_partitions = {"under 1k": 3, "1k to 100k": 12, "100k plus": 48}
            n_parts = mps_partitions.get(self.msg_mps, 3)
            config["messaging"] = {self.messaging: {"topics": [{"name": "default", "partitions": n_parts}]}}
        
        if self.gateway != "none":
            config["gateway"] = {"provider": self.gateway}

        # Storage
        if "minio" in self.databases or "minio" in self.features or "file_upload" in self.features:
            config["storage"] = {"provider": "minio", "buckets": self.storage_buckets}
        
        # API & Features
        if self.api_framework != "none":
            api_conf = {"framework": self.api_framework, "max_concurrency": self.max_rps}
            config["api"] = api_conf
            
        if "auth" in self.features:
            config["auth"] = {"provider": "postgres", "pattern": self.auth_pattern}
            
        # MLOps
        if self.enable_mlops:
            config["mlops"] = {
                "serving": self.ml_serving,
                "tracking": self.ml_tracking,
                "orchestration": self.ml_orchestration,
                "monitoring": self.ml_monitoring,
                "vector_dbs": self.ml_vector_dbs,
                "agents": self.ml_agents,
                "caching": self.ml_caching,
                "training_enabled": self.ml_training_enabled,
                "embedding_dim": self.ml_embedding_dim
            }
            if self.ml_training_enabled:
                config["mlops"]["orchestrator"] = self.ml_orchestrator

            # Vector DBs also go into databases
            for vdb in self.ml_vector_dbs:
                config.setdefault("databases", {})[vdb] = {}

        # Observability alerting
        if self.observability == "full" and self.alert_channels:
            chan_map = {
                "Slack webhook": "slack",
                "PagerDuty": "pagerduty",
                "email": "email",
            }
            channels = []
            for c in self.alert_channels:
                if c in chan_map:
                    channels.append({"type": chan_map[c]})
            if channels:
                config.setdefault("observability", {})["alerting"] = {"channels": channels}

        # Features flat list
        all_features = list(self.features)
        if "multi-tenancy" in all_features:
            config.setdefault("features_config", {})["multi-tenancy"] = {"strategy": self.tenancy_model}
            
        if all_features:
            config["features"] = all_features

        return config

    def should_show(self, q_id: str) -> bool:
        """Determines if a question should be asked based on state."""
        # Database related
        if q_id in ["db_extensions", "pg_replicas", "pgbouncer", "db_migrations"]:
            return len(self.databases) > 0
        
        # Messaging related
        if q_id in ["msg_topics", "msg_partitions", "msg_consumer_groups", "msg_dlq", "msg_outbox", "msg_mps"]:
            return self.messaging != "none"
            
        # Cache related
        if q_id in ["cache_ttl", "cache_eviction", "cache_cluster"]:
            return self.cache != "none"
            
        # Storage related
        if q_id in ["storage_buckets", "storage_types", "file_upload_presigned"]:
            return "minio" in self.databases or "minio" in self.features or "file_upload" in self.features
            
        # Cloud provider
        if q_id == "cloud_provider":
            return self.target == "kubernetes"
            
        # LLM Serving related
        if q_id in ["ml_vector_dbs", "ml_agents", "ml_caching"]:
            return len(self.ml_serving) > 0
            
        # Deploy targets
        if q_id in ["tf_section", "cloud_provider", "managed_services", "prod_replicas"]:
            return self.target != "local"
        if q_id in ["docker_ports", "docker_volumes"]:
            return self.target != "kubernetes"
            
        # Observability
        if q_id == "alert_delivery":
            return self.observability == "full"
            
        # MLOps Section
        if q_id == "mlops_section":
            return self.enable_mlops
            
        # Misc rules
        if q_id == "auth_pattern":
            return "auth" in self.features
        if q_id == "tenancy_model":
            return "multi-tenancy" in self.features
        if q_id == "max_rps":
            return self.scale == "large"
        if q_id == "ml_training_jobs":
            return "mlflow" in self.ml_tracking
        if q_id == "ml_orchestrator":
            return self.ml_training_enabled
        if q_id == "ml_embedding_dim":
            return "qdrant" in self.ml_vector_dbs
            
        return True

    def skip_reason(self, q_id: str) -> str:
        """Returns the reason a question was skipped."""
        if q_id in ["db_extensions", "pg_replicas", "pgbouncer", "db_migrations"]:
            return "No databases selected."
        if q_id in ["msg_topics", "msg_partitions", "msg_consumer_groups", "msg_dlq", "msg_outbox", "msg_mps"]:
            return "No messaging selected."
        if q_id in ["cache_ttl", "cache_eviction", "cache_cluster"]:
            return "No cache selected."
        if q_id in ["storage_buckets", "storage_types", "file_upload_presigned"]:
            return "No storage selected."
        if q_id in ["ml_vector_dbs", "ml_agents", "ml_caching"]:
            return "No LLM serving module selected."
        if q_id in ["tf_section", "managed_services", "prod_replicas"]:
            return "Local deploy target."
        if q_id == "cloud_provider":
            return "Not deploying to Kubernetes."
        if q_id in ["docker_ports", "docker_volumes"]:
            return "Kubernetes deploy target."
        if q_id == "alert_delivery":
            return "Full observability not selected."
        if q_id == "mlops_section":
            return "No MLOps modules selected at all."
        if q_id == "auth_pattern":
            return "Auth feature not selected."
        if q_id == "tenancy_model":
            return "Multi-tenancy feature not selected."
        if q_id == "max_rps":
            return "Scale is not large."
        if q_id == "ml_training_jobs":
            return "MLflow not selected in tracking."
        if q_id == "ml_orchestrator":
            return "Training jobs not enabled."
        if q_id == "ml_embedding_dim":
            return "Qdrant not selected."
            
        return "Skipped based on previous answers."

    def validate_current_state(self) -> None:
        """Validates the current state against the actual Pydantic schema."""
        load_config_from_dict(self.to_config_dict())

    def notify_auto_add(self, module: str, reason: str, trigger: str) -> None:
        """Visual notification for auto-added modules."""
        self.auto_added_modules.add(module)
        content = (
            f"[bold cyan]⚡ Auto-Added:[/bold cyan] {module}\n"
            f"[bold white]Reason:[/bold white] {reason}\n"
            f"[bold white]Triggered by:[/bold white] {trigger}"
        )
        console.print(Panel(
            content,
            border_style="yellow",
            padding=(0, 2)
        ))

# ──────────────────────────── Wizard Engine ────────────────────────────

class SetupWizard:
    def __init__(self) -> None:
        self.state = WizardState()
        self.current_step = 0
        self.edit_mode = False
        self.skipped_notes: list[str] = []
        
        self.steps = [
            ("Project Basics", self._step_basics),
            ("Infrastructure", self._step_infra),
            ("Features & Components", self._step_features),
            ("MLOps & AI", self._step_mlops),
            ("Data Models", self._step_models),
            ("Review & Generate", self._step_confirmation)
        ]

    def run(self) -> dict[str, Any]:
        console.print("\n[bold success]NIKAME — Interactive Setup Wizard[/bold success] 🚀")
        console.print("[dim]Define your stack. We build the glue.[/dim]\n")
        
        while self.current_step < len(self.steps):
            name, step_fn = self.steps[self.current_step]
            
            # Smart Elimination Logic
            skip = False
            if name == "MLOps & AI" and not self.state.enable_mlops:
                skip = True
                self.skipped_notes.append("Skipped MLOps section (not enabled).")
            
            if skip:
                self.current_step += 1
                continue
                
            try:
                # Print skipped notes if any
                if self.skipped_notes:
                    for note in self.skipped_notes:
                        console.print(f"[dim]→ {note}[/dim]")
                    self.skipped_notes = []

                step_fn()
                self.state.completed_steps.add(self.current_step)
                
                # In normal flow, just go to next
                if not self.edit_mode:
                    self.current_step += 1
                else:
                    # In edit mode, if we finished the step we wanted, go to confirmation
                    # UNLESS we invalidated further steps
                    if (self.current_step + 1) in self.state.completed_steps:
                        self.current_step = len(self.steps) - 1
                    else:
                        self.current_step += 1
            except KeyboardInterrupt:
                console.print("\n[warning]KeyboardInterrupt caught. Use 'Cancel' in review or finish the step.[/warning]")
                continue
            except Exception as e:
                console.print(f"\n[bold red]❌ Validation Error:[/bold red] {e}")
                console.print("[dim]Please correct your input below.[/dim]\n")
                # Stay on the same step

        return self.state.to_config_dict()

    # ── STEP 1: Basics ──
    def _step_basics(self) -> None:
        console.print(Panel("[bold cyan]Step 1: Project Basics[/bold cyan]", expand=False))
        
        self.state.name = questionary.text(
            "What is your project name?",
            default=self.state.name,
            validate=lambda x: len(x.strip()) > 0 or "Name cannot be empty"
        ).ask()

        self.state.target = questionary.select(
            "Where do you want to deploy?",
            choices=["local", "kubernetes", "aws", "gcp"],
            default=self.state.target
        ).ask()

        self.state.profile = questionary.select(
            "Target environment profile?",
            choices=["local", "staging", "production"],
            default=self.state.profile
        ).ask()

        # Immediate Validation
        self.state.validate_current_state()

    # ── STEP 2: Infrastructure ──
    def _step_infra(self) -> None:
        console.print(Panel("[bold cyan]Step 2: Infrastructure[/bold cyan]", expand=False))
        
        # 1. Databases
        db_choices = [
            questionary.Choice("postgres  — Relational (standard)", value="postgres", 
                               checked=("postgres" in self.state.databases)),
            questionary.Choice("mongodb   — Document / Schemaless", value="mongodb",
                               checked=("mongodb" in self.state.databases)),
            questionary.Choice("clickhouse — High-perf Analytics", value="clickhouse",
                               checked=("clickhouse" in self.state.databases)),
            questionary.Choice("neo4j     — Graph DB", value="neo4j",
                               checked=("neo4j" in self.state.databases)),
        ]

        self.state.databases = questionary.checkbox(
            "Select core databases:",
            choices=db_choices
        ).ask() or []
        
        # Follow-up: Postgres
        if self.state.should_show("pg_replicas"):
            if "postgres" in self.state.databases:
                has_replicas = questionary.confirm("Will you need Postgres read replicas?", default=False).ask()
                if has_replicas:
                    self.state.pg_replicas = int(questionary.select("How many read replicas?", choices=["1", "2", "3"]).ask())
        else:
            console.print(f"[dim]→ Skipped Postgres replicas: {self.state.skip_reason('pg_replicas')}[/dim]")

        # 2. Cache — Dragonfly removes Redis from choices (Phase 2 rule)
        cache_choices = [
            questionary.Choice("dragonfly (recommended)", value="dragonfly"),
            questionary.Choice("none", value="none")
        ]
        # Only show Redis if Dragonfly not already selected
        if self.state.cache != "dragonfly":
            cache_choices.insert(1, questionary.Choice("redis", value="redis"))
        
        self.state.cache = questionary.select(
            "Cache provider:",
            choices=cache_choices,
            default=self.state.cache
        ).ask()

        # Follow-up: Cache options (e.g. eviction, cluster)
        if self.state.should_show("cache_ttl"):
            pass  # Future detailed cache questions
        else:
            console.print(f"[dim]→ Skipped cache details: {self.state.skip_reason('cache_ttl')}[/dim]")

        # 3. Messaging (Incompatibility Block & Smart Elimination)
        while True:
            messaging_selections = questionary.checkbox(
                "Messaging backend (Select up to one):",
                choices=["redpanda", "kafka", "rabbitmq"]
            ).ask() or []
            
            # Phase 4: Hard Incompatibility Block
            if "kafka" in messaging_selections and "redpanda" in messaging_selections:
                console.print(Panel("[bold red]These are both Kafka-compatible brokers. Select only one.[/bold red]", border_style="red"))
                continue
                
            if len(messaging_selections) > 1:
                console.print(Panel("[bold red]Only one messaging backend is supported right now.[/bold red]", border_style="red"))
                continue
                
            self.state.messaging = messaging_selections[0] if messaging_selections else "none"
            break

        # Follow-up: Messaging throughput
        if self.state.should_show("msg_mps"):
            if self.state.messaging in ["redpanda", "kafka"]:
                self.state.msg_mps = questionary.select(
                    "Estimated messages per second?",
                    choices=["under 1k", "1k to 100k", "100k plus"],
                    default=self.state.msg_mps
                ).ask()
        else:
            console.print(f"[dim]→ Skipped messaging topics & partitions: {self.state.skip_reason('msg_mps')}[/dim]")

        # 4. Gateway
        self.state.gateway = questionary.select(
            "API Gateway:",
            choices=["traefik", "nginx", "none"],
            default=self.state.gateway
        ).ask()

        # 5. Observability (needed for alert_delivery follow-up)
        self.state.observability = questionary.select(
            "Observability stack:",
            choices=["full", "lightweight", "none"],
            default=self.state.observability
        ).ask()

        # Follow-up: Alert delivery (Phase 5)
        if self.state.should_show("alert_delivery"):
            self.state.alert_channels = questionary.checkbox(
                "Alert delivery channels:",
                choices=["Slack webhook", "PagerDuty", "email", "none"]
            ).ask() or []
        else:
            console.print(f"[dim]→ Skipped alert delivery: {self.state.skip_reason('alert_delivery')}[/dim]")

        self.state.validate_current_state()

    # ── STEP 3: Features ──
    def _step_features(self) -> None:
        console.print(Panel("[bold cyan]Step 3: Features & Components[/bold cyan]", expand=False))
        
        # 1. API Framework (Incompatibility Block: Only one)
        while True:
            api_selections = questionary.checkbox(
                "API Framework(s):",
                choices=["fastapi", "flask", "django"] # Added options to allow multi-select failure
            ).ask() or []
            
            if len(api_selections) > 1:
                console.print(Panel("[bold red]Only one API framework is supported. Select only one.[/bold red]", border_style="red"))
                continue
                
            self.state.api_framework = api_selections[0] if api_selections else "none"
            break

        # 2. Features Selection
        base_features = [
            ("auth", "User Authentication"),
            ("multi-tenancy", "Multi-tenant logic"),
            ("file_upload", "File Storage & Uploads"),
            ("background_jobs", "AsyncTask Support"),
            ("admin_panel", "Internal Operations Admin"),
            ("keycloak", "Keycloak SSO"),
            ("authentik", "Authentik SSO"),
        ]
        
        from nikame.codegen.registry import COMPONENT_REGISTRY
        all_choices = []
        
        # Smart Elimination: Auth requires database
        auth_disabled = not self.state.databases
        if auth_disabled:
            self.skipped_notes.append("Auth requires a database. (Select one in Infrastructure to enable manually, or auto-add later)")

        for key, title in base_features:
            all_choices.append(questionary.Choice(
                title=f"{key} — {title}", 
                value=key,
                checked=(key in self.state.features)
            ))
            
        for key, info in COMPONENT_REGISTRY.items():
            all_choices.append(questionary.Choice(
                title=f"[{info['category']}] {info['name']}", 
                value=key,
                checked=(key in self.state.features)
            ))

        while True:
            self.state.features = questionary.checkbox(
                "Select Application Features & Components:",
                choices=all_choices
            ).ask() or []

            # Auth Provider Incompatibility
            auth_providers = [f for f in self.state.features if f in ["keycloak", "authentik", "auth"]]
            # Actually, "auth" is general, "keycloak" and "authentik" are specific. 
            # Prompt specifically says: Keycloak and Authentik both selected
            specific_auth = [f for f in self.state.features if f in ["keycloak", "authentik"]]
            if len(specific_auth) > 1:
                console.print(Panel("[bold red]Only one auth provider is supported. Select only one.[/bold red]", border_style="red"))
                continue
            break

        # 3. Auto-add Logic with Notifications
        if "auth" in self.state.features and not self.state.databases:
            self.state.databases.append("postgres")
            self.state.notify_auto_add("postgres", "Auth requires a database.", "auth feature selection")
            
        if "background_jobs" in self.state.features and self.state.cache == "none":
            self.state.cache = "dragonfly"
            self.state.notify_auto_add("dragonfly", "Background jobs require a cache.", "background_jobs feature selection")
            
        if "multi-tenancy" in self.state.features and "auth" not in self.state.features:
            self.state.features.append("auth")
            self.state.notify_auto_add("auth", "Multi-tenancy requires authentication.", "multi-tenancy feature selection")
            if "postgres" not in self.state.databases and not self.state.databases:
                self.state.databases.append("postgres")
                self.state.notify_auto_add("postgres", "Auth requires a database.", "auth feature auto-add")
            
        if "file_upload" in self.state.features:
            if "minio" not in self.state.databases and "minio" not in self.state.features:
                self.state.features.append("minio")
                self.state.notify_auto_add("minio", "File uploads require object storage.", "file_upload feature selection")

        # 4. Contextual Follow-ups
        if self.state.should_show("auth_pattern"):
             self.state.auth_pattern = questionary.select(
                 "What auth pattern?",
                 choices=["JWT stateless", "JWT with refresh tokens", "session based"],
                 default=self.state.auth_pattern
             ).ask()
        else:
             console.print(f"[dim]→ Skipped auth pattern: {self.state.skip_reason('auth_pattern')}[/dim]")
             
        if self.state.should_show("tenancy_model"):
            self.state.tenancy_model = questionary.select(
                "Tenancy model?",
                choices=["separate schemas", "row-level security", "separate databases"],
                default=self.state.tenancy_model
            ).ask()
        else:
            console.print(f"[dim]→ Skipped tenancy model: {self.state.skip_reason('tenancy_model')}[/dim]")

        # Follow-up: MinIO storage types (Phase 5)
        if self.state.should_show("storage_types"):
            self.state.storage_buckets = questionary.checkbox(
                "What will you store in MinIO?",
                choices=["user uploads", "ML models", "backups", "exports"]
            ).ask() or []
        else:
            console.print(f"[dim]→ Skipped storage types: {self.state.skip_reason('storage_types')}[/dim]")

        # Scale Follow-up
        self.state.scale = questionary.select(
            "Select project scale:",
            choices=["small", "medium", "large"],
            default=self.state.scale
        ).ask()
        
        if self.state.should_show("max_rps"):
            self.state.max_rps = int(questionary.text(
                "Expected peak requests per second?",
                default=str(self.state.max_rps)
            ).ask())
        else:
            console.print(f"[dim]→ Skipped peak RPS config: {self.state.skip_reason('max_rps')}[/dim]")

        # Follow-up: K8s cloud (Phase 5)
        if self.state.should_show("cloud_provider"):
            self.state.cloud_provider = questionary.select(
                "Which cloud?",
                choices=["AWS EKS", "GCP GKE", "Azure AKS", "bare-metal"],
                default=self.state.cloud_provider
            ).ask()
        else:
            console.print(f"[dim]→ Skipped cloud provider: {self.state.skip_reason('cloud_provider')}[/dim]")

        self.state.generate_guide = questionary.confirm(
            "Generate project-specific GUIDE.md?",
            default=self.state.generate_guide
        ).ask()

        self.state.validate_current_state()

    # ── STEP 4: MLOps ──
    def _step_mlops(self) -> None:
        console.print(Panel("[bold cyan]Step 4: MLOps & AI Configuration[/bold cyan]", expand=False))

        # 1. Serving (The anchor for everything else)
        while True:
            self.state.ml_serving = questionary.checkbox(
                "🚀 Model Serving — How will you serve AI models?",
                choices=[
                    questionary.Choice("vllm", value="vllm", checked=("vllm" in self.state.ml_serving)),
                    questionary.Choice("ollama", value="ollama", checked=("ollama" in self.state.ml_serving)),
                    questionary.Choice("llamacpp", value="llamacpp", checked=("llamacpp" in self.state.ml_serving)),
                    questionary.Choice("triton", value="triton", checked=("triton" in self.state.ml_serving)),
                ]
            ).ask() or []
            
            # Phase 4 Incompatibility: Mixing vLLM and llama.cpp
            if "vllm" in self.state.ml_serving and "llamacpp" in self.state.ml_serving:
                console.print(Panel("[bold red]Select one serving engine per model. You cannot mix vLLM and llama.cpp here.[/bold red]", border_style="red"))
                continue
            
            # Phase 4 Incompatibility: vLLM on small scale
            if "vllm" in self.state.ml_serving and self.state.scale == "small":
                console.print(Panel("[bold yellow]vLLM requires significant GPU resources and is not recommended for small scale. Ollama or llama.cpp are better fits.[/bold yellow]", border_style="yellow"))
                warn = questionary.confirm("Continue anyway?", default=False).ask()
                if not warn:
                    continue # Re-selection needed
            break

        # Smart Elimination: If no serving, everything else is skipped
        if not self.state.ml_serving:
            self.state.enable_mlops = False
            self.skipped_notes.append("No LLM serving module selected — skipping vector DB, agents, and LLM caching.")
            return
            
        self.state.enable_mlops = True

        # 2. Tracking
        self.state.ml_tracking = questionary.checkbox(
            "📊 Experiment Tracking / Versioning:",
            choices=[
                questionary.Choice("mlflow", value="mlflow", checked=("mlflow" in self.state.ml_tracking)),
                questionary.Choice("dvc", value="dvc", checked=("dvc" in self.state.ml_tracking)),
            ]
        ).ask() or []
        
        if self.state.should_show("ml_training_jobs"):
            self.state.ml_training_enabled = questionary.confirm("Will you run training jobs?", default=False).ask()
            if self.state.should_show("ml_orchestrator"):
                self.state.ml_orchestrator = questionary.select(
                    "Which orchestrator?",
                    choices=["prefect", "airflow", "zenml", "none"],
                    default=self.state.ml_orchestrator
                ).ask()
            else:
                console.print(f"[dim]→ Skipped ML orchestrator: {self.state.skip_reason('ml_orchestrator')}[/dim]")
        else:
            console.print(f"[dim]→ Skipped training jobs: {self.state.skip_reason('ml_training_jobs')}[/dim]")

        # ... (Other MLOps multi-selects) ...
        self.state.ml_vector_dbs = questionary.checkbox(
            "🧠 Vector Databases (ML Store):",
            choices=[
                questionary.Choice("qdrant", value="qdrant", checked=("qdrant" in self.state.ml_vector_dbs)),
                questionary.Choice("pgvector", value="pgvector", checked=("pgvector" in self.state.ml_vector_dbs)),
            ]
        ).ask() or []
        
        # Phase 3 Auto-add for semantic search
        if ("semantic-search" in self.state.features or "rag-pipeline" in self.state.features) and not self.state.ml_vector_dbs:
            add_vdb = questionary.confirm("Semantic search needs a vector DB. Add Qdrant?", default=True).ask()
            if add_vdb:
                self.state.ml_vector_dbs.append("qdrant")
                self.state.notify_auto_add("qdrant", "Semantic search component selected with no vector DB.", "semantic-search/rag-pipeline selection")
        
        # Follow-up: Qdrant
        if self.state.should_show("ml_embedding_dim"):
             self.state.ml_embedding_dim = int(questionary.select(
                 "Embedding model?",
                 choices=[
                     questionary.Choice("OpenAI ada-002 (1536 dims)", value="1536"),
                     questionary.Choice("sentence-transformers (384 dims)", value="384"),
                     questionary.Choice("custom (ask for dimensions)", value="768"),
                 ]
             ).ask())
        else:
             console.print(f"[dim]→ Skipped embedding dim: {self.state.skip_reason('ml_embedding_dim')}[/dim]")

        self.state.validate_current_state()

    # ── STEP 5: Models ──
    def _step_models(self) -> None:
        console.print(Panel("[bold cyan]Step 5: Data Model Builder[/bold cyan]", expand=False))
        if self.state.models and not questionary.confirm("Keep existing data models?").ask():
           self.state.models = {}
           
        if not self.state.models:
            self.state.models = _get_models_logic()
        
        self.state.validate_current_state()

    # ── STEP 6: Confirmation ──
    def _step_confirmation(self) -> None:
        config_dict = self.state.to_config_dict()
        _print_confirmation_screen(config_dict)
        
        choice = questionary.select(
            "Ready to build?",
            choices=[
                questionary.Choice("🚀 Looks good, generate my project", value="Build"),
                questionary.Choice("📝 Edit a section", value="Edit"),
                questionary.Choice("❌ Cancel", value="Cancel")
            ]
        ).ask()

        if choice == "Build":
            # Success, exit loop
            self.current_step = 100
        elif choice == "Cancel":
            console.print("[warning]Generation cancelled.[/warning]")
            raise SystemExit(0)
        else:
            self.edit_mode = True
            edit_choices = [
                questionary.Choice(self.steps[i][0], value=i)
                for i in range(len(self.steps) - 1)
                if i in self.state.completed_steps
            ]
            self.current_step = questionary.select(
                "Which section do you want to edit?",
                choices=edit_choices
            ).ask()


# ──────────────────────────── Helper Logic ────────────────────────────

def run_wizard() -> dict[str, Any]:
    """Entry point for the init wizard."""
    use_template = questionary.select(
        "Start from a template? (saves time)",
        choices=[
            "Search templates",
            "Skip, start fresh"
        ]
    ).ask()
    
    wizard = SetupWizard()
    
    if use_template == "Search templates":
        from nikame.registry.client import RegistryClient
        client = RegistryClient()
        query = questionary.text("Search templates (e.g. rag, saas):").ask()
        results = client.search(query or "", sort="stars")
        
        if results:
            choices = [f"{r['name']} ({r['id']})" for r in results]
            choices.append("Cancel")
            selected = questionary.select("Select a template:", choices=choices).ask()
            
            if selected and selected != "Cancel":
                template_id = selected.split("(")[1].split(")")[0]
                template = client.get_template(template_id)
                if template:
                    raw = {k: v for k, v in template["raw"].items() if k != "registry_meta"}
                    
                    new_name = questionary.text("What is your new project name?").ask()
                    wizard.state.name = new_name or raw.get("name", "my-project")
                    
                    # Hydrate state
                    if "project" in raw:
                        if "scale" in raw["project"]:
                            wizard.state.scale = raw["project"]["scale"]
                        if "access_pattern" in raw["project"]:
                            wizard.state.access_pattern = raw["project"]["access_pattern"]
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
                        if "serving" in raw["mlops"]:
                            wizard.state.ml_serving = raw["mlops"]["serving"]
                        if "vector_dbs" in raw["mlops"]:
                            wizard.state.ml_vector_dbs = raw["mlops"]["vector_dbs"]
                    if "features" in raw:
                        wizard.state.features = raw["features"]
                        
                    wizard.current_step = len(wizard.steps) - 1 # Jump to confirmation
        else:
            console.print("[dim]No templates found. Starting fresh.[/dim]")
            
    return wizard.run()

def _get_models_logic() -> dict[str, Any]:
    """Extracted model builder logic."""
    models = {}
    while True:
        model_name = questionary.text("Model name (empty to finish):").ask()
        if not model_name: break
        
        model_def = {"fields": {}, "relationships": {}}
        while True:
            f_name = questionary.text(f"[{model_name}] Field name (empty to finish):").ask()
            if not f_name: break
            
            f_type = questionary.select(f"[{model_name}.{f_name}] Type:",
                                     choices=["str", "int", "float", "bool", "datetime", "enum", "relationship"]).ask()
            
            if f_type == "relationship":
                target = questionary.text("Target model:").ask()
                rel = questionary.select("Type:", choices=["many-to-one", "one-to-many"]).ask()
                model_def["relationships"][f_name] = {"model": target, "type": rel}
            else:
                model_def["fields"][f_name] = {"type": f_type}
        
        models[model_name] = model_def
    return models

def _print_confirmation_screen(config: dict[str, Any]) -> None:
    """Rich display of the final configuration."""
    console.clear()
    console.print(Panel("[bold green]NIKAME — FINAL REVIEW[/bold green]", expand=False))
    
    summary = Table(box=None, padding=(0, 2), show_header=False)
    summary.add_row("[cyan]Project Info[/cyan]", f"{config['name']} ([dim]{config['project']['scale']}[/dim])")
    summary.add_row("[cyan]Environment[/cyan]", f"{config['environment']['target']} / {config['environment']['profile']}")
    
    infra = []
    
    def _format_infra(module_name: str, extra: str = "") -> str:
        base = f"✓ {module_name}{extra}"
        if module_name in config.get('_auto_added', set()):
            base += " [dim](auto-added)[/dim]"
        return base
        
    # We pass auto_added_modules via a temp hidden key because we don't serialize it normally
    auto_added = config.get('_auto_added', set())

    if "databases" in config: 
        for db, conf in config["databases"].items():
             extra = f" ([dim]{conf['replicas']} replicas[/dim])" if conf.get("replicas", 1) > 1 else ""
             infra.append(_format_infra(db, extra))
             
    if "cache" in config: infra.append(_format_infra(config['cache']['provider']))
    if "messaging" in config: infra.append(_format_infra(list(config['messaging'].keys())[0]))
    summary.add_row("[cyan]Infrastructure[/cyan]", "\n".join(infra))
    
    if "mlops" in config:
        ml = []
        for k, v in config["mlops"].items():
            if v and isinstance(v, list): ml.append(f"[bold]{k.title()}:[/bold] {', '.join(v)}")
            elif v and k == "embedding_dim": ml.append(f"[bold]Embeddings:[/bold] {v}d")
        summary.add_row("[cyan]MLOps[/cyan]", "\n".join(ml))
        
    # Matrix Engine Section — show which integrations would trigger
    try:
        from nikame.config.loader import NikameConfig
        from nikame.codegen.integrations.base import BaseIntegration
        import importlib, pkgutil
        
        cfg_dict = dict(config)
        cfg_dict.pop("_auto_added", None)
        cfg = NikameConfig.model_validate(cfg_dict)
        
        # Build blueprint to get active modules
        from nikame.blueprint.engine import _extract_active_modules
        active_modules_dict = _extract_active_modules(cfg)
        active_module_names = set(active_modules_dict.keys())
        active_feature_names = set(cfg.features or [])
        
        # Discover and check integrations
        import nikame.codegen.integrations as integ_pkg
        from pathlib import Path
        integ_path = Path(integ_pkg.__file__).parent
        
        triggered_names = []
        for _, modname, _ in pkgutil.walk_packages([str(integ_path)], prefix="nikame.codegen.integrations."):
            if modname.split(".")[-1] in ("base", "matrix", "__init__"):
                continue
            try:
                mod = importlib.import_module(modname)
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BaseIntegration) and attr is not BaseIntegration:
                        if attr.should_trigger(active_module_names, active_feature_names):
                            # Use a clean display name
                            display = attr.__name__.replace("Integration", "").replace("_", " ")
                            triggered_names.append(display)
            except Exception:
                pass
        
        if triggered_names:
            summary.add_row("[cyan]Matrix Engine[/cyan]", "\n".join([f"✓ {n}" for n in triggered_names]))
        else:
            summary.add_row("[cyan]Matrix Engine[/cyan]", "[dim]None detected[/dim]")
    except Exception:
        summary.add_row("[cyan]Matrix Engine[/cyan]", "[dim]None detected[/dim]")

    
    # Calculate a slightly more dynamic (but still estimated) cost based on modules
    base_cost = 45.0
    infra_count = len(config.get("databases", {})) + (1 if config.get("cache") else 0) + (1 if config.get("messaging") else 0)
    estimated_cost = base_cost + (infra_count * 15.0)
    if config["project"]["scale"] == "large": estimated_cost *= 3
    
    console.print(summary)
    console.print(f"\n[dim]Estimated Monthly Infrastructure Cost: [bold yellow]~${estimated_cost:.2f}[/bold yellow][/dim]\n")

def _show_confirmation(config_dict: dict[str, Any]) -> str:
    """Stand-alone confirmation screen for existing configs."""
    _print_confirmation_screen(config_dict)
    
    choice = questionary.select(
        "Ready to build?",
        choices=[
            questionary.Choice("🚀 Looks good, generate my project", value="Build"),
            questionary.Choice("📝 Edit a section", value="Edit"),
            questionary.Choice("❌ Cancel", value="Cancel")
        ]
    ).ask()
    return choice
