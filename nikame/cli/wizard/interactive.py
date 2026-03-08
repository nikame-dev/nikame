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

PROJECT_TYPES = [
    "saas", "marketplace", "content_platform", "api_service",
    "data_pipeline", "ml_platform", "internal_tool", "ecommerce", "rag_app"
]

@dataclass
class WizardState:
    """Manages wizard state, validation, and cascading invalidation."""
    
    # 1. Project Basics
    name: str = "my-app"
    target: Literal["local", "kubernetes", "aws", "gcp"] = "local"
    profile: Literal["local", "staging", "production"] = "local"
    project_type: str = "saas"
    
    # 2. Infrastructure
    databases: list[str] = field(default_factory=list)
    cache: str = "dragonfly"
    messaging: str = "none"
    gateway: str = "traefik"
    observability: str = "none"
    ci_cd: list[str] = field(default_factory=list)
    
    # 3. Features & Components
    api_framework: str = "fastapi"
    features: list[str] = field(default_factory=list)
    generate_guide: bool = True
    
    # 4. MLOps (Optional)
    enable_mlops: bool = False
    ml_serving: list[str] = field(default_factory=list)
    ml_tracking: list[str] = field(default_factory=list)
    ml_orchestration: list[str] = field(default_factory=list)
    ml_monitoring: list[str] = field(default_factory=list)
    ml_vector_dbs: list[str] = field(default_factory=list)
    ml_agents: list[str] = field(default_factory=list)
    ml_caching: list[str] = field(default_factory=list)
    
    # 5. Data Models
    models: dict[str, Any] = field(default_factory=dict)
    
    # Tracking dirty steps for cascading invalidation
    completed_steps: set[int] = field(default_factory=set)

    def to_config_dict(self) -> dict[str, Any]:
        """Assembles the actual NikameConfig dictionary."""
        config = {
            "name": self.name,
            "environment": {"target": self.target, "profile": self.profile},
            "project": {
                "type": self.project_type,
                "scale": "small", # Default scale for init
                "access_pattern": "balanced",
            },
            "generate_guide": self.generate_guide,
            "models": self.models,
        }

        # Infra
        if self.databases:
            config["databases"] = {db: {} for db in self.databases}
        if self.cache != "none":
            config["cache"] = {"provider": self.cache}
        if self.messaging != "none":
            config["messaging"] = {self.messaging: {}}
        if self.gateway != "none":
            config["gateway"] = {"provider": self.gateway}
        
        # API & Features
        if self.api_framework != "none":
            config["api"] = {"framework": self.api_framework}
        
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
            }
            # Vector DBs also go into databases
            for vdb in self.ml_vector_dbs:
                config.setdefault("databases", {})[vdb] = {}

        # Features flat list
        all_features = list(self.features)
        if all_features:
            config["features"] = all_features

        return config

    def validate_current_state(self) -> None:
        """Validates the current state against the actual Pydantic schema."""
        load_config_from_dict(self.to_config_dict())

    def apply_type_presets(self) -> None:
        """Applies smart defaults based on the project_type."""
        tp = self.project_type
        
        # 1. MLOps enablement
        if tp in ["ml_platform", "data_pipeline", "rag_app"]:
            self.enable_mlops = True
        
        # 2. Infra presets
        if tp == "ml_platform":
            self.databases = ["postgres"]
            self.cache = "dragonfly"
            self.ml_vector_dbs = ["qdrant"]
        elif tp == "rag_app":
            self.ml_vector_dbs = ["qdrant"]
            self.ml_agents = ["langchain"]
        elif tp == "data_pipeline":
            self.messaging = "redpanda"
            self.databases = ["clickhouse"]
        elif tp == "ecommerce":
            self.databases = ["postgres", "mongodb"]
            self.cache = "redis"

    def invalidate_from(self, step_idx: int) -> None:
        """Clears all steps from a certain index onwards."""
        self.completed_steps = {s for s in self.completed_steps if s < step_idx}


# ──────────────────────────── Wizard Engine ────────────────────────────

class SetupWizard:
    def __init__(self) -> None:
        self.state = WizardState()
        self.current_step = 0
        self.edit_mode = False
        
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
            
            # Skip MLOps if not auto-enabled and not manually requested
            if name == "MLOps & AI" and not self.state.enable_mlops:
                self.current_step += 1
                continue
                
            try:
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

        old_type = self.state.project_type
        self.state.project_type = questionary.select(
            "What kind of project is this?",
            choices=PROJECT_TYPES,
            default=self.state.project_type
        ).ask()

        # Cascading Invalidation
        if self.state.project_type != old_type:
            console.print("[dim]Project type changed. Re-applying presets...[/dim]")
            self.state.apply_type_presets()
            self.state.invalidate_from(1) 

        # Immediate Validation
        self.state.validate_current_state()

    # ── STEP 2: Infrastructure ──
    def _step_infra(self) -> None:
        console.print(Panel("[bold cyan]Step 2: Infrastructure[/bold cyan]", expand=False))
        
        # Databases (NO Vector DBs here anymore)
        db_choices = [
            questionary.Choice("postgres  — Relational (standard)", value="postgres", 
                               checked=("postgres" in self.state.databases)),
            questionary.Choice("mongodb   — Document / Schemaless", value="mongodb",
                               checked=("mongodb" in self.state.databases)),
        ]
        if self.state.project_type in ["data_pipeline", "ml_platform"]:
            db_choices.append(questionary.Choice("clickhouse — High-perf Analytics", value="clickhouse",
                                                checked=("clickhouse" in self.state.databases)))
        
        db_choices.append(questionary.Choice("neo4j     — Graph DB", value="neo4j",
                                            checked=("neo4j" in self.state.databases)))

        self.state.databases = questionary.checkbox(
            "Select core databases:",
            choices=db_choices
        ).ask() or []

        self.state.cache = questionary.select(
            "Cache provider:",
            choices=["dragonfly", "redis", "none"],
            default=self.state.cache
        ).ask()

        self.state.messaging = questionary.select(
            "Messaging backend:",
            choices=["redpanda", "kafka", "rabbitmq", "none"],
            default=self.state.messaging
        ).ask()

        self.state.gateway = questionary.select(
            "API Gateway:",
            choices=["traefik", "nginx", "none"],
            default=self.state.gateway
        ).ask()

        self.state.validate_current_state()

    # ── STEP 3: Features ──
    def _step_features(self) -> None:
        console.print(Panel("[bold cyan]Step 3: Features & Components[/bold cyan]", expand=False))
        
        self.state.api_framework = questionary.select(
            "API Framework:",
            choices=["fastapi", "none"],
            default=self.state.api_framework
        ).ask()

        base_features = [
            ("auth", "User Authentication"),
            ("profiles", "User Profiles"),
            ("file_upload", "File Storage & Uploads"),
            ("email", "Transactional Email"),
            ("payments", "Stripe Integration"),
            ("background_jobs", "AsyncTask Support"),
            ("admin_panel", "Internal Operations Admin"),
            ("search", "Full-text Search engine"),
        ]
        
        # Merge with Advanced Components
        from nikame.codegen.registry import COMPONENT_REGISTRY
        
        all_choices = []
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

        self.state.features = questionary.checkbox(
            "Select Application Features & Components:",
            choices=all_choices
        ).ask() or []

        self.state.generate_guide = questionary.confirm(
            "Generate project-specific GUIDE.md?",
            default=self.state.generate_guide
        ).ask()

        self.state.validate_current_state()

    # ── STEP 4: MLOps ──
    def _step_mlops(self) -> None:
        console.print(Panel("[bold cyan]Step 4: MLOps & AI Configuration[/bold cyan]", expand=False))
        
        if self.state.project_type not in ["ml_platform", "data_pipeline", "rag_app"]:
            self.state.enable_mlops = questionary.confirm(
                "Enable MLOps & AI capabilities?",
                default=self.state.enable_mlops
            ).ask()
            
            if not self.state.enable_mlops:
                return

        # Sequential multi-selects for MLOps tools
        self.state.ml_serving = questionary.checkbox(
            "🚀 Model Serving — How will you serve AI models?",
            choices=[
                questionary.Choice("vllm", value="vllm", checked=("vllm" in self.state.ml_serving)),
                questionary.Choice("ollama", value="ollama", checked=("ollama" in self.state.ml_serving)),
                questionary.Choice("llamacpp", value="llamacpp", checked=("llamacpp" in self.state.ml_serving)),
                questionary.Choice("tgi", value="tgi", checked=("tgi" in self.state.ml_serving)),
                questionary.Choice("triton", value="triton", checked=("triton" in self.state.ml_serving)),
                questionary.Choice("localai", value="localai", checked=("localai" in self.state.ml_serving)),
                questionary.Choice("xinference", value="xinference", checked=("xinference" in self.state.ml_serving)),
                questionary.Choice("airllm", value="airllm", checked=("airllm" in self.state.ml_serving)),
                questionary.Choice("bentoml", value="bentoml", checked=("bentoml" in self.state.ml_serving)),
            ]
        ).ask() or []

        self.state.ml_tracking = questionary.checkbox(
            "📊 Experiment Tracking / Versioning:",
            choices=[
                questionary.Choice("mlflow", value="mlflow", checked=("mlflow" in self.state.ml_tracking)),
                questionary.Choice("dvc", value="dvc", checked=("dvc" in self.state.ml_tracking)),
            ]
        ).ask() or []

        self.state.ml_orchestration = questionary.checkbox(
            "🔄 Pipeline Orchestration:",
            choices=[
                questionary.Choice("prefect", value="prefect", checked=("prefect" in self.state.ml_orchestration)),
                questionary.Choice("airflow", value="airflow", checked=("airflow" in self.state.ml_orchestration)),
                questionary.Choice("zenml", value="zenml", checked=("zenml" in self.state.ml_orchestration)),
            ]
        ).ask() or []

        self.state.ml_monitoring = questionary.checkbox(
            "🔍 Monitoring & Observability:",
            choices=[
                questionary.Choice("evidently", value="evidently", checked=("evidently" in self.state.ml_monitoring)),
                questionary.Choice("langfuse", value="langfuse", checked=("langfuse" in self.state.ml_monitoring)),
                questionary.Choice("arize-phoenix", value="arize-phoenix", checked=("arize-phoenix" in self.state.ml_monitoring)),
            ]
        ).ask() or []

        self.state.ml_vector_dbs = questionary.checkbox(
            "🧠 Vector Databases (ML Store):",
            choices=[
                questionary.Choice("qdrant", value="qdrant", checked=("qdrant" in self.state.ml_vector_dbs)),
                questionary.Choice("weaviate", value="weaviate", checked=("weaviate" in self.state.ml_vector_dbs)),
                questionary.Choice("milvus", value="milvus", checked=("milvus" in self.state.ml_vector_dbs)),
                questionary.Choice("chroma", value="chroma", checked=("chroma" in self.state.ml_vector_dbs)),
                questionary.Choice("pgvector", value="pgvector", checked=("pgvector" in self.state.ml_vector_dbs)),
            ]
        ).ask() or []

        self.state.ml_agents = questionary.checkbox(
            "🤖 Agent Frameworks:",
            choices=[
                questionary.Choice("langchain", value="langchain", checked=("langchain" in self.state.ml_agents)),
                questionary.Choice("llamaindex", value="llamaindex", checked=("llamaindex" in self.state.ml_agents)),
                questionary.Choice("haystack", value="haystack", checked=("haystack" in self.state.ml_agents)),
            ]
        ).ask() or []

        self.state.ml_caching = questionary.checkbox(
            "⚡ LLM Caching (Response Reuse):",
            choices=[
                questionary.Choice("gptcache", value="gptcache", checked=("gptcache" in self.state.ml_caching)),
            ]
        ).ask() or []

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
            choices = [f"{r['name']} ({r['id']}) - {r['stars']} ⭐" for r in results]
            choices.append("Cancel")
            selected = questionary.select("Select a template:", choices=choices).ask()
            
            if selected and selected != "Cancel":
                template_id = selected.split("(")[1].split(")")[0]
                template = client.get_template(template_id)
                if template:
                    raw = {k: v for k, v in template["raw"].items() if k != "registry_meta"}
                    
                    new_name = questionary.text("What is your new project name?").ask()
                    wizard.state.project_name = new_name or raw.get("name", "my-project")
                    
                    # Hydrate state
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
    summary.add_row("[cyan]Project Info[/cyan]", f"{config['name']} ({config['project']['type']})")
    summary.add_row("[cyan]Environment[/cyan]", f"{config['environment']['target']} / {config['environment']['profile']}")
    
    infra = []
    if "databases" in config: infra.extend([f"✓ {d}" for d in config["databases"]])
    if "cache" in config: infra.append(f"✓ {config['cache']['provider']}")
    summary.add_row("[cyan]Infrastructure[/cyan]", "\n".join(infra))
    
    if "mlops" in config:
        ml = []
        for k, v in config["mlops"].items():
            if v: ml.append(f"[bold]{k.title()}:[/bold] {', '.join(v)}")
        summary.add_row("[cyan]MLOps[/cyan]", "\n".join(ml))
    
    console.print(summary)
    console.print("\n[dim]Estimated Monthly Infrastructure Cost: [bold yellow]~$85.00[/bold yellow][/dim]\n")

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
