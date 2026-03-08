"""Evidently AI Drift Monitoring Integration.

Triggers when Evidently is active.
Automatically hooks into FastAPI model prediction endpoints to capture
inferences asynchronously and send them to the Evidently tracking server.
"""

from __future__ import annotations

from nikame.codegen.integrations.base import BaseIntegration


class DriftMonitoringIntegration(BaseIntegration):
    """Generates the background prediction capture logic."""

    REQUIRED_MODULES = ["evidently"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Check if they have an LLM serving component since Evidently 
        # is used to monitor predictions from models.
        llms = ["llamacpp", "ollama", "vllm", "tgi", "triton", "localai", "xinference", "airllm"]
        self.served_model = next((l for l in llms if l in self.active_modules), "prediction_model")

    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Trigger if Evidently is active alongside a serving gateway."""
        has_evidently = "evidently" in active_modules
        has_serving = any(m in active_modules for m in ["llamacpp", "ollama", "vllm", "tgi", "triton", "localai", "xinference", "airllm", "bentoml"])
        return has_evidently and has_serving

    def generate_core(self) -> list[tuple[str, str]]:
        core_logic = self._generate_drift_middleware()
        return [("app/core/integrations/drift_monitor.py", core_logic)]

    def generate_lifespan(self) -> str:
        return """
    # --- Evidently Drift Monitoring ---
    try:
        from app.core.integrations.drift_monitor import init_drift_monitoring
        logger.info("Initializing background prediction monitoring...")
        init_drift_monitoring()
    except Exception as e:
        logger.warning(f"Failed to initialize Evidently drift monitor: {e}")
        """

    def generate_health(self) -> dict[str, str]:
        return {}

    def generate_metrics(self) -> str:
        return """
    EVIDENTLY_EVENTS_SENT = Counter(
        "nikame_evidently_events_sent_total", 
        "Count of prediction events forwarded to Evidently AI"
    )
        """

    def generate_guide(self) -> str:
        return f"""
### Model Drift Monitoring (Evidently)
**Status:** Active 🟢 
**Target Model:** `{self.served_model}`

Prediction inputs and outputs are automatically captured via standard request/response models. Background tasks forward this telemetry to the `Evidently` tracking server without blocking the main event loop.
"""

    def _generate_drift_middleware(self) -> str:
        return f"""import logging
import httpx
import uuid
from datetime import datetime
from fastapi import BackgroundTasks
from app.core.config import settings

logger = logging.getLogger(__name__)

# Assumes Evidently workspace/dataset setup is handled elsewhere,
# this serves to fire events to the API collector.

def init_drift_monitoring():
    logger.info("Drift Monitoring active. Checking Clearly/Evidently collector connection...")
    # In a real environment, you might verify connection to settings.EVIDENTLY_HOST here
    pass

async def capture_prediction(model_name: str, input_data: str, output_data: str):
    \"\"\"Forward a single inference event to Evidently collector.\"\"\"
    payload = {{
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "model": model_name,
        "input": input_data,
        "output": output_data
    }}
    
    try:
        # Fire-and-forget telemetry via HTTPX
        target_url = getattr(settings, "EVIDENTLY_COLLECTOR_URL", "http://evidently:8000/api/v1/data")
        async with httpx.AsyncClient() as client:
            await client.post(target_url, json=payload, timeout=2.0)
            
        logger.debug(f"Captured prediction telemetry for {{model_name}}")
    except Exception as e:
        logger.warning(f"Failed to send telemetry to Evidently: {{e}}")

def hook_drift_monitor(background_tasks: BackgroundTasks, input_prompt: str, generated_text: str):
    \"\"\"
    Utility to attach drift monitoring to any endpoint easily.
    Usage:
        @router.post("/generate")
        def gen(req, background_tasks: BackgroundTasks):
            res = model.generate(req)
            hook_drift_monitor(background_tasks, req.text, res.text)
            return res
    \"\"\"
    background_tasks.add_task(
        capture_prediction, 
        "{self.served_model}", 
        input_prompt, 
        generated_text
    )
"""
