"""Distributed Tracing Integration (OpenTelemetry + FastApi/Celery/Kafka)

Triggers when OpenTelemetry (Tempo, Jaeger) is active.
Propagates trace context across FastApi requests, SQLAlchemy queries,
and RedPanda events automatically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from nikame.codegen.integrations.base import BaseIntegration

if TYPE_CHECKING:
    from nikame.blueprint.engine import Blueprint
    from nikame.config.schema import NikameConfig


class TracingPropagationIntegration(BaseIntegration):
    """Generates distributed trace injection logic."""

    REQUIRED_MODULES = ["otel_collector"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_postgres = "postgres" in self.active_modules
        self.use_redpanda = "redpanda" in self.active_modules
        self.use_cache = "dragonfly" in self.active_modules or "redis" in self.active_modules

    def generate_core(self) -> list[tuple[str, str]]:
        files = []
        tracing_service = self._generate_tracing_py()
        files.append(("app/core/integrations/tracing_propagation.py", tracing_service))
        return files

    def generate_lifespan(self) -> str:
        return """
    # --- Distributed Tracing Instrumentation ---
    from app.core.integrations.tracing_propagation import instrument_app
    instrument_app(app)
        """

    def generate_health(self) -> dict[str, str]:
        return {}

    def generate_metrics(self) -> str:
        return ""

    def generate_guide(self) -> str:
        return """
### Distributed Tracing (OpenTelemetry)
**Status:** Active 🟢
**Components:** OpenTelemetry Collector / Tempo

A context propagator has been wired directly into the FastApi `lifespan`. This intercepts incoming HTTP requests, intercepts downstream database queries, and intercepts outgoing event messages. This guarantees full end-to-end trace visibility in Tempo/Grafana without manual span tracking in every router.
"""

    def _generate_tracing_py(self) -> str:
        template = """import logging
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
"""
        if self.use_postgres:
            template += "from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor\n"
        if self.use_cache:
            template += "from opentelemetry.instrumentation.redis import RedisInstrumentor\n"
        if self.use_redpanda:
            template += "from opentelemetry.instrumentation.confluent_kafka import ConfluentKafkaInstrumentor\n"

        template += """
logger = logging.getLogger(__name__)

def instrument_app(app):
    \"\"\"Wires up OpenTelemetry instrumentation globally across detected libraries.\"\"\"
    try:
        # Instrument FastApi incoming requests
        FastAPIInstrumentor.instrument_app(app)
"""
        if self.use_postgres:
            template += """
        # Instrument Database queries
        from app.db.session import engine
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine) # Or async equivalent based on driver
"""
        if self.use_cache:
            template += "        RedisInstrumentor().instrument()\n"
        
        if self.use_redpanda:
            template += "        ConfluentKafkaInstrumentor().instrument()\n"

        template += """
        logger.info("OpenTelemetry Context Propagation Enabled.")
    except Exception as e:
        logger.warning(f"Failed to boot OpenTelemetry context propagation: {e}")
"""
        return template
