import asyncio
from arq import create_pool
from arq.connections import RedisSettings

# Mocking a heavy task
async def process_inference(ctx, input_data: str):
    print(f"Starting inference for: {input_data}")
    # Simulate heavy model work
    await asyncio.sleep(5)
    result = f"Worker result for {input_data}"
    print(f"Finished inference: {result}")
    return result

async def startup(ctx):
    # Load model here for the worker process
    # ctx['model'] = load_my_model()
    print("Worker started and model loaded.")

async def shutdown(ctx):
    print("Worker shutting down.")

class WorkerSettings:
    """
    Configuration for the ARQ worker.
    """
    functions = [process_inference]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn("{{REDIS_URL}}" or "redis://localhost:6379/0")
