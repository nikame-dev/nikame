import asyncio
import httpx
import logging
from uuid import uuid4
from typing import Any, Dict, Optional
from pydantic import BaseModel, HttpUrl

logger = logging.getLogger("app.ai_infra.jobs")

class JobRequest(BaseModel):
    input_data: Any
    webhook_url: Optional[HttpUrl] = None

class JobStatus(BaseModel):
    job_id: str
    status: str
    result: Optional[Any] = None

# In-memory job store (Use Redis for production)
jobs_db: Dict[str, JobStatus] = {}

async def process_job(job_id: str, input_data: Any, webhook_url: Optional[str], model: Any):
    """
    Background task to run inference and notify via webhook.
    """
    try:
        jobs_db[job_id].status = "processing"
        
        # Simulate heavy inference
        await asyncio.sleep(2) 
        result = f"Processed: {input_data}"
        
        jobs_db[job_id].status = "completed"
        jobs_db[job_id].result = result
        
        # Notify via webhook if URL provided
        if webhook_url:
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(webhook_url, json={
                        "job_id": job_id,
                        "status": "completed",
                        "result": result
                    })
                except Exception as e:
                    logger.error(f"Webhook delivery failed for job {job_id}: {e}")
                    
    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        jobs_db[job_id].status = "failed"
