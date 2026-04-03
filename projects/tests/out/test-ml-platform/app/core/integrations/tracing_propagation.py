import logging
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

logger = logging.getLogger(__name__)

def instrument_app(app):
    """Wires up OpenTelemetry instrumentation globally across detected libraries."""
    try:
        # Instrument FastApi incoming requests
        FastAPIInstrumentor.instrument_app(app)

        # Instrument Database queries
        from app.db.session import engine
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine) # Or async equivalent based on driver
        RedisInstrumentor().instrument()

        logger.info("OpenTelemetry Context Propagation Enabled.")
    except Exception as e:
        logger.warning(f"Failed to boot OpenTelemetry context propagation: {e}")
