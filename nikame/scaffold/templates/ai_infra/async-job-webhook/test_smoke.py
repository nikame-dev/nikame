import pytest
import asyncio
from app.ai_infra.async_jobs import JobStatus, jobs_db, process_job

@pytest.mark.asyncio
async def test_job_processing():
    job_id = "test-job"
    jobs_db[job_id] = JobStatus(job_id=job_id, status="queued")
    
    await process_job(job_id, "test input", None, None)
    
    assert jobs_db[job_id].status == "completed"
    assert "test input" in jobs_db[job_id].result
