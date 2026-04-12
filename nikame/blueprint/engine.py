"""Blueprint engine — resolves module dependencies into a generation plan.
"""

from __future__ import annotations
import networkx as nx 
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional

from nikame.config.schema import NikameConfig
from nikame.modules.base import BaseModule, ModuleContext
from nikame.modules.registry import discover_modules, get_all_modules, get_module_class
from nikame.utils.logger import get_logger

_log = get_logger("blueprint.engine")

@dataclass
class Blueprint:
    project_name: str
    modules: list[BaseModule]
    graph: nx.DiGraph
    config: NikameConfig | None = None
    env_vars: dict[str, str] = field(default_factory=dict)
    features: list[str] = field(default_factory=list)

class BlueprintEngine:
    def __init__(self, config: NikameConfig):
        self.config = config

    def resolve(self) -> Blueprint:
        return build_blueprint(self.config)

def build_blueprint(config: NikameConfig) -> Blueprint:
    discover_modules()
    active_module_configs = _extract_active_modules(config)
    
    graph: nx.DiGraph = nx.DiGraph()
    for mod_name in active_module_configs:
        graph.add_node(mod_name)

    # Topological Sort
    sorted_nodes = list(nx.topological_sort(graph))
    
    resolved_modules = []
    accumulated_env = {}
    for mod_name in sorted_nodes:
        mod_cls = get_module_class(mod_name)
        if mod_cls:
            # FIX: BaseModule.__init__ requires (config, ctx) in that order
            ctx = ModuleContext(
                project_name=config.name,
                namespace=config.name,
                active_modules=list(active_module_configs.keys())
            )
            # Pass (config: dict, ctx: ModuleContext)
            mod_inst = mod_cls(active_module_configs.get(mod_name, {}), ctx)
            resolved_modules.append(mod_inst)
            accumulated_env.update(mod_inst.env_vars())

    return Blueprint(
        project_name=config.name,
        modules=resolved_modules,
        graph=graph,
        config=config,
        env_vars=accumulated_env,
        features=config.features or []
    )

def _extract_active_modules(config: NikameConfig) -> dict[str, dict[str, Any]]:
    modules: dict[str, dict[str, Any]] = {}
    
    # ── API & Auth ──
    if config.api:
        api_name = config.api.framework if hasattr(config.api, "framework") else config.api.get("framework")
        if api_name:
            modules[api_name] = config.api if isinstance(config.api, dict) else config.api.model_dump()

    if config.auth:
        auth_name = config.auth.provider if hasattr(config.auth, "provider") else config.auth.get("provider")
        if auth_name:
            modules[auth_name] = config.auth if isinstance(config.auth, dict) else config.auth.model_dump()

    # ── Databases ──
    if config.databases:
        db_data = config.databases if isinstance(config.databases, dict) else config.databases.model_dump()
        for name, cfg in db_data.items():
            if cfg:
                modules[name] = cfg

    # ── Messaging ──
    if config.messaging:
        msg_data = config.messaging if isinstance(config.messaging, dict) else config.messaging.model_dump()
        for name, cfg in msg_data.items():
            if cfg:
                modules[name] = cfg

    # ── MLOps (Models & Vector DBs) ──
    if config.mlops:
        ml_data = config.mlops if isinstance(config.mlops, dict) else config.mlops.model_dump()
        
        # Models
        if ml_data.get("models"):
            modules["ml-gateway"] = {}
        
        # Vector Databases
        vector_dbs = ml_data.get("vector_dbs", [])
        for vdb in vector_dbs:
            modules[vdb] = {}

    return modules
