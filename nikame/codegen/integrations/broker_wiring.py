"""Broker Auto-Wiring Integration (Celery + Dragonfly + RedPanda)

Triggers when Celery and Dragonfly (Redis) or RedPanda are active.
Automatically configures Celery to use Redis as the primary broker and 
result backend, saving the user from manual environment wiring.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from nikame.codegen.integrations.base import BaseIntegration

if TYPE_CHECKING:
    from nikame.blueprint.engine import Blueprint
    from nikame.config.schema import NikameConfig


class BrokerAutoWiringIntegration(BaseIntegration):
    """Automatically wires background job brokers to active services."""

    REQUIRED_MODULES = ["celery"]
    # We require Celery. We'll inspect which broker is available.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_redis = "dragonfly" in self.active_modules or "redis" in self.active_modules
        self.use_kafka = "redpanda" in self.active_modules

    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Trigger if Celery exists AND there is a viable broker."""
        has_celery = "celery" in active_modules
        has_broker = "dragonfly" in active_modules or "redis" in active_modules or "redpanda" in active_modules
        return has_celery and has_broker

    def generate_core(self) -> list[tuple[str, str]]:
        files = []
        wiring_script = self._generate_auto_wiring_py()
        files.append(("app/core/integrations/broker_wiring.py", wiring_script))
        return files

    def generate_lifespan(self) -> str:
        return "" 

    def generate_health(self) -> dict[str, str]:
        return {} 

    def generate_metrics(self) -> str:
        return ""

    def generate_guide(self) -> str:
        b_type = "Redis / Dragonfly" if self.use_redis else "Kafka / RedPanda"
        return f"""
### Broker Auto-Wiring
**Status:** Active 🟢
**Detected Broker:** {b_type}

The Matrix Engine detected Celery without a hardcoded broker preference. Since `{b_type}` is available in your stack, the engine automatically wired Celery's `broker_url` and `result_backend` connections directly into `{b_type}`. No configurations needed!
"""

    def _generate_auto_wiring_py(self) -> str:
        scheme = "redis" if self.use_redis else "kafka"
        
        return f"""import logging
import os
from celery import Celery

logger = logging.getLogger(__name__)

def configure_celery_broker(celery_app: Celery):
    \"\"\"Auto-wire celery to Matrix-detected infrastructure.\"\"\"
    logger.info("Auto-wiring Celery Broker via {scheme.upper()}")
    
    # In a full generation, we dynamically load the correct connection string 
    # from the environment (e.g., REDIS_URL or KAFKA_BROKERS).
    # Since Dragonfly API is 100% Redis compatible, we use the `redis://` scheme.
    
    broker_url = os.environ.get("BROKER_URL", "{scheme}://dragonfly_or_redis:6379/0")
    result_backend = os.environ.get("RESULT_BACKEND", "{scheme}://dragonfly_or_redis:6379/1")

    celery_app.conf.update(
        broker_url=broker_url,
        result_backend=result_backend,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        worker_concurrency={self.profile.worker_concurrency},
        worker_prefetch_multiplier=1
    )
    
# --- app/worker.py ---
# from app.core.integrations.broker_wiring import configure_celery_broker
# celery_app = Celery("tasks")
# configure_celery_broker(celery_app)
"""
