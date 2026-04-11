# Async Job Webhook

A pattern for handling long-running AI tasks without blocking the HTTP request.

## Workflow

1. **Submit**: Client `POST`s data and an optional `webhook_url`.
2. **Accept**: Server returns a `job_id` and `202 Accepted` immediately.
3. **Execute**: Server runs inference in a `BackgroundTasks` or Celery worker.
4. **Notify**: Server sends a `POST` request to the client's `webhook_url` when finished.

## Usage

Mount the router:

```python
from app.routers.jobs import router as jobs_router
app.include_router(jobs_router)
```

## Why it matters

User-facing HTTP requests shouldn't last longer than a few seconds. If your ML model takes 10+ seconds to run (e.g., video generation), you *must* use an asynchronous job pattern.

## Gotchas

- **Reliability**: This implementation uses in-memory storage and `BackgroundTasks`. If the server restarts, queued jobs are lost. For production, use **Celery** or **ARQ** with Redis/Postgres persistence.
- **Webhook Security**: Consider signing webhook payloads so the client can verify they originated from your server.
- **Retry Logic**: This pattern does not automatically retry failed webhook deliveries.
