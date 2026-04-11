from arq import create_pool
from arq.connections import RedisSettings

REDIS_URL = "{{REDIS_URL}}" or "redis://localhost:6379/0"

class JobService:
    """
    Helper service to enqueue jobs from the FastAPI application.
    """
    def __init__(self):
        self.redis = None

    async def connect(self):
        self.redis = await create_pool(RedisSettings.from_dsn(REDIS_URL))

    async def enqueue_inference(self, input_data: str):
        if not self.redis:
            await self.connect()
        # Returns a Job object
        return await self.redis.enqueue_job('process_inference', input_data)

job_service = JobService()
