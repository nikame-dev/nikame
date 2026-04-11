import asyncio
import time
from uuid import uuid4
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from fastapi import FastAPI

@dataclass
class BatchItem:
    id: str
    input: Any
    future: asyncio.Future

class DynamicBatcher:
    """
    Collects multiple single requests and processes them as one large batch.
    Dramatically increases GPU throughput.
    """
    def __init__(self, max_batch_size: int = 8, wait_ms: int = 50):
        self.max_batch_size = max_batch_size
        self.wait_ms = wait_ms / 1000.0
        self.queue = asyncio.Queue()
        self.worker_task = None

    async def start(self, model: Any):
        self.worker_task = asyncio.create_task(self._worker(model))

    async def stop(self):
        if self.worker_task:
            self.worker_task.cancel()

    async def add(self, input_data: Any) -> Any:
        # Create a "ticket" (future) that will be fulfilled by the worker
        future = asyncio.get_event_loop().create_future()
        item = BatchItem(id=str(uuid4()), input=input_data, future=future)
        await self.queue.put(item)
        return await future

    async def _worker(self, model: Any):
        while True:
            # Wait for at least one item
            first_item = await self.queue.get()
            batch = [first_item]
            
            # Try to grab more items until max_batch_size or wait_ms is reached
            start_time = time.perf_counter()
            while len(batch) < self.max_batch_size:
                remaining_wait = self.wait_ms - (time.perf_counter() - start_time)
                if remaining_wait <= 0:
                    break
                
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=remaining_wait)
                    batch.append(item)
                except asyncio.TimeoutError:
                    break

            # Process the batch
            try:
                inputs = [b.input for b in batch]
                # Simulate batch inference: outputs = model.generate_batch(inputs)
                outputs = [f"Result for {i}" for i in inputs]
                
                for i, output in enumerate(outputs):
                    if not batch[i].future.done():
                        batch[i].future.set_result(output)
            except Exception as e:
                for item in batch:
                    if not item.future.done():
                        item.future.set_exception(e)
            finally:
                for _ in range(len(batch)):
                    self.queue.task_done()
