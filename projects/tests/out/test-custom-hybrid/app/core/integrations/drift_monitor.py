import logging
import httpx
import uuid
from datetime import datetime
from fastapi import BackgroundTasks
from app.core.config import settings

import os
from tenacity import retry, stop_after_attempt, wait_exponential, before_log
import logging

logger = logging.getLogger(__name__)
MAX_RETRIES = int(os.getenv('MAX_RETRY_ATTEMPTS', '3'))

logger = logging.getLogger(__name__)

# Assumes Evidently workspace/dataset setup is handled elsewhere,
# this serves to fire events to the API collector.

def init_drift_monitoring():
    logger.info("Drift Monitoring active. Checking Clearly/Evidently collector connection...")
    # In a real environment, you might verify connection to settings.EVIDENTLY_HOST here
    pass

async def capture_prediction(model_name: str, input_data: str, output_data: str):
    """Forward a single inference event to Evidently collector."""
    payload = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "model": model_name,
        "input": input_data,
        "output": output_data
    }
    
    try:
        # Fire-and-forget telemetry via HTTPX
        target_url = getattr(settings, "EVIDENTLY_COLLECTOR_URL", "http://evidently:8000/api/v1/data")
        async with httpx.AsyncClient() as client:
            await client.post(target_url, json=payload, timeout=2.0)
            
        logger.debug(f"Captured prediction telemetry for {model_name}")
    except Exception as e:
        logger.warning(f"Failed to send telemetry to Evidently: {e}")

def hook_drift_monitor(background_tasks: BackgroundTasks, input_prompt: str, generated_text: str):
    """
    Utility to attach drift monitoring to any endpoint easily.
    Usage:
        @router.post("/generate")
        def gen(req, background_tasks: BackgroundTasks):
            res = model.generate(req)
            hook_drift_monitor(background_tasks, req.text, res.text)
            return res
    """
    background_tasks.add_task(
        capture_prediction, 
        "ollama", 
        input_prompt, 
        generated_text
    )