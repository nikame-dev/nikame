from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from nikame.codegen.base import BaseCodegen

_CODEGEN_REGISTRY: dict[str, type[BaseCodegen]] = {}

def register_codegen(cls: type[BaseCodegen]) -> type[BaseCodegen]:
    """Decorator to register a codegen feature."""
    _CODEGEN_REGISTRY[cls.NAME] = cls
    return cls

def get_codegen_class(name: str) -> type[BaseCodegen] | None:
    """Return the codegen class for a given feature name."""
    return _CODEGEN_REGISTRY.get(name)

def discover_codegen() -> None:
    """Dynamically discover and import all codegen features."""
    import nikame.codegen.features as features
    for loader, module_name, is_pkg in pkgutil.walk_packages(features.__path__, features.__name__ + "."):
        importlib.import_module(module_name)

# High-fidelity components (Grouped for Item 2)
from nikame.codegen.components.api_keys import APIKeyCodegen
from nikame.codegen.components.audit_log import AuditLogCodegen
from nikame.codegen.components.cron_jobs import CronJobsCodegen
from nikame.codegen.components.graphql import GraphQLCodegen
from nikame.codegen.components.grpc import GRPCCodegen
from nikame.codegen.components.health_check import HealthCheckCodegen
from nikame.codegen.components.mock_data import MockDataCodegen
from nikame.codegen.components.multi_tenancy import MultiTenancyCodegen
from nikame.codegen.components.pubsub import PubSubCodegen
from nikame.codegen.components.rate_limiting import RateLimitingCodegen
from nikame.codegen.components.sse import SSECodegen
from nikame.codegen.components.stripe import StripeCodegen
from nikame.codegen.components.vector_search import VectorSearchCodegen
from nikame.codegen.components.webhooks import WebhookCodegen
from nikame.codegen.components.websocket import WebSocketCodegen
from nikame.codegen.components.storage_service import StorageServiceCodegen
from nikame.codegen.features.streamlit import StreamlitCodegen

from nikame.codegen.ml_gateway import MLGatewayCodegen
from nikame.codegen.schema_codegen import SchemaCodegen

# Register all components and core codegens
for cls in [
    GraphQLCodegen, GRPCCodegen, WebSocketCodegen, WebhookCodegen,
    APIKeyCodegen, MockDataCodegen, AuditLogCodegen, VectorSearchCodegen,
    SSECodegen, PubSubCodegen, MultiTenancyCodegen, CronJobsCodegen,
    StripeCodegen, HealthCheckCodegen, RateLimitingCodegen,
    StorageServiceCodegen, StreamlitCodegen, MLGatewayCodegen, SchemaCodegen
]:
    register_codegen(cls)

COMPONENT_REGISTRY: dict[str, dict[str, Any]] = {
    # APIs
    "graphql": {
        "category": "APIs",
        "name": "GraphQL API (Strawberry)",
        "class": GraphQLCodegen
    },
    "grpc": {
        "category": "APIs",
        "name": "gRPC service",
        "class": GRPCCodegen
    },
    "websocket": {
        "category": "APIs",
        "name": "WebSocket server",
        "class": WebSocketCodegen
    },
    "webhooks": {
        "category": "APIs",
        "name": "Webhook receiver",
        "class": WebhookCodegen
    },
    "api_key": {
        "category": "APIs",
        "name": "Public API key system",
        "class": APIKeyCodegen
    },
    "mock_data": {
        "category": "APIs",
        "name": "Mock data generator",
        "class": MockDataCodegen
    },
    # Data & Search
    "vector_search": {
        "category": "Data",
        "name": "Semantic Vector Search (Qdrant)",
        "class": VectorSearchCodegen
    },
    "audit_log": {
        "category": "Data",
        "name": "Audit Logs (History Tracking)",
        "class": AuditLogCodegen
    },
    # Real-time & Events
    "sse": {
        "category": "Real-time",
        "name": "Server-Sent Events (SSE)",
        "class": SSECodegen
    },
    "pubsub": {
        "category": "Real-time",
        "name": "Redis Pub/Sub",
        "class": PubSubCodegen
    },
    # Teams
    "multi_tenancy": {
        "category": "Teams",
        "name": "Multi-tenancy (Org isolation)",
        "class": MultiTenancyCodegen
    },
    # Jobs
    "cron_jobs": {
        "category": "Jobs",
        "name": "Cron Jobs (Celery)",
        "class": CronJobsCodegen
    },
    # Billing
    "stripe": {
        "category": "Billing",
        "name": "Stripe Integration",
        "class": StripeCodegen
    },
    # Dev Tools
    "rate_limiting": {
        "category": "Dev Tools",
        "name": "Redis Rate Limiting",
        "class": RateLimitingCodegen
    },
    "health_check": {
        "category": "Dev Tools",
        "name": "Health Check Dashboard",
        "class": HealthCheckCodegen
    },
    "streamlit": {
        "category": "Frontend",
        "name": "Streamlit RAG Playground",
        "class": StreamlitCodegen
    }
}
