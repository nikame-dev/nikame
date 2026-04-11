from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from app.ai_infra.model_loader import get_model
from app.ai_infra.async_jobs import JobRequest, JobStatus, jobs_db, process_job, str

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("/", response_model=JobStatus)
async def create_job(
    request: JobRequest, 
    background_tasks: BackgroundTasks,
    model: Any = Depends(get_model)
):
    """
    Creates an async job and returns the job ID immediately.
    The actual inference runs in the background.
    """
    job_id = str(uuid4())
    job = JobStatus(job_id=job_id, status="queued")
    jobs_db[job_id] = job
    
    background_tasks.add_task(
        process_job, 
        job_id, 
        request.input_data, 
        str(request.webhook_url) if request.webhook_url else None,
        model
    )
    
    return job

@router.get("/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """
    Poll the status of an existing job.
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs_db[job_id]
