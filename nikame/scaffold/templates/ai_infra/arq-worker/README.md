# ARQ Worker

A production-grade asynchronous job queue using Redis. Unlike `BackgroundTasks`, ARQ runs in a separate process, meaning a crashed worker won't take down your API, and you can scale workers independently of your web nodes.

## Usage

1. **Start the Worker**:
   Run the following command in your project root:
   ```bash
   arq app.ai_infra.worker.WorkerSettings
   ```

2. **Enqueue from FastAPI**:
   ```python
   from app.ai_infra.worker_service import job_service

   @app.post("/jobs")
   async def create_job(data: str):
       job = await job_service.enqueue_inference(data)
       return {"id": job.job_id}
   ```

## Why ARQ?

ARQ is extremely lightweight, async-native, and uses Redis for high performance. It's the spiritual successor to Celery for the modern Python ecosystem.

## Gotchas

-   **Persistence**: Ensure your Redis instance is configured with persistence (AOF/RDB) if you want to survive Redis restarts.
-   **Class Serialization**: ARQ uses `pickle` for task arguments. Ensure your inputs are serializable.
