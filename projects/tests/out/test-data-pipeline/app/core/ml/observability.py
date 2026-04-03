"""
ML Observability and Tracing configuration.
"""
import os
import logging
from core.config import settings

logger = logging.getLogger(__name__)

def init_observability(app=None):
    """Initialize LangFuse, Arize Phoenix, and Evidently integrations."""

    # Configure Evidently UI connections (Placeholder for dataset routing)
    os.environ["EVIDENTLY_HOST"] = getattr(settings, "EVIDENTLY_HOST", "http://localhost:8085")
    logger.info("Evidently AI integration ready")
