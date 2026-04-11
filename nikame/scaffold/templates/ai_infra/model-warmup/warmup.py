import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, List

logger = logging.getLogger("app.ai_infra.warmup")

async def run_model_warmup(
    model: Any,
    inference_func: Callable[[Any, Any], Coroutine[Any, Any, Any]],
    warmup_inputs: List[Any],
    iterations: int = 1
):
    """
    Executes dummy inference passes to ensure GPU kernels are compiled
    and CUDA context is fully initialized.
    """
    logger.info(f"Starting model warmup ({iterations} iterations)...")
    start_total = time.perf_counter()
    
    for i in range(iterations):
        for idx, start_input in enumerate(warmup_inputs):
            start_pass = time.perf_counter()
            try:
                # We don't care about the output, just the execution
                await inference_func(model, start_input)
                end_pass = time.perf_counter()
                logger.debug(f"Warmup pass {i+1}, input {idx+1} took {end_pass - start_pass:.4f}s")
            except Exception as e:
                logger.error(f"Warmup pass {i+1} failed: {e}")

    end_total = time.perf_counter()
    logger.info(f"Model warmup completed in {end_total - start_total:.2f}s")

def warmup_lifespan_wrapper(
    original_lifespan: Callable,
    inference_func: Callable,
    warmup_inputs: List[Any],
    iterations: int = 1
):
    """
    Higher-order function to wrap a lifespan to include warmup logic.
    """
    from fastapi import FastAPI
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def wrapped_lifespan(app: FastAPI):
        async with original_lifespan(app):
            # Assumes model is stored in app.state by original_lifespan
            model = app.state.model_manager.model
            await run_model_warmup(model, inference_func, warmup_inputs, iterations)
            yield
            
    return wrapped_lifespan
