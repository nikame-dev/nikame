"""Async Inference Pipeline Integration.

Triggers when RedPanda (Kafka) is active alongside any ML Serving module.
Auto-configures an asynchronous message queue for long-running LLM/ML
generations, routing requests to a worker and returning results via topics.
"""

from __future__ import annotations

from nikame.codegen.integrations.base import BaseIntegration


class AsyncInferenceIntegration(BaseIntegration):
    """Generates an asynchronous Kafka-based inference queue."""

    REQUIRED_MODULES = ["redpanda"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        llms = ["llamacpp", "ollama", "vllm", "tgi", "triton", "localai", "xinference", "airllm", "bentoml", "whisper", "tts"]
        self.served_model = next((l for l in llms if l in self.active_modules), None)

    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Trigger if a Kafka-compatible broker is active alongside a serving gateway."""
        has_kafka = "redpanda" in active_modules or "kafka" in active_modules
        has_serving = any(m in active_modules for m in ["llamacpp", "ollama", "vllm", "tgi", "triton", "localai", "xinference", "airllm", "bentoml", "whisper", "tts"])
        return has_kafka and has_serving

    def generate_core(self) -> list[tuple[str, str]]:
        if not self.served_model:
            return []
            
        core_logic = self._generate_async_worker()
        return [("app/workers/inference_queue.py", core_logic)]

    def generate_lifespan(self) -> str:
        return """
    # --- Async Inference Queue ---
    try:
        from app.workers.inference_queue import start_inference_consumer
        import asyncio
        # Run Kafka consumer in background
        asyncio.create_task(start_inference_consumer())
        logger.info("Async Inference Queue consumer started.")
    except Exception as e:
        logger.warning(f"Failed to start async inference consumer: {e}")
        """

    def generate_health(self) -> dict[str, str]:
        return {}

    def generate_metrics(self) -> str:
        return """
    ASYNC_INFERENCES_PROCESSED = Counter(
        "nikame_async_inference_processed_total", 
        "Count of long-running inference tasks completed via Kafka"
    )
        """

    def generate_guide(self) -> str:
        return f"""
### Asynchronous Inference Queue (RedPanda)
**Status:** Active 🟢 
**Target Engine:** `{self.served_model}`

Large requests to `{self.served_model}` can be slow. Since RedPanda is active, an asynchronous request/reply message broker has been auto-configured.

1. Publish generation requests to the `inference.requests` Kafka topic.
2. The `app.workers.inference_queue` consumer picks them up, processes them against the LLM, and publishes the result to the `inference.responses` topic.
"""

    def _generate_async_worker(self) -> str:
        return f"""import json
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from core.config import settings
from services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)

# Topics
REQUEST_TOPIC = "inference.requests"
RESPONSE_TOPIC = "inference.responses"

async def process_message(producer: AIOKafkaProducer, message_value: bytes):
    try:
        req = json.loads(message_value.decode("utf-8"))
        job_id = req.get("job_id", "unknown")
        prompt = req.get("prompt", "")
        
        logger.info(f"Processing async inference job {{job_id}}...")
        
        # Dispatch to the active gateway
        result = await LLMGateway.generate_completion(prompt)
        
        # Publish response
        res_payload = json.dumps({{"job_id": job_id, "status": "complete", "result": result}})
        await producer.send_and_wait(RESPONSE_TOPIC, res_payload.encode("utf-8"))
        
        logger.info(f"Completed job {{job_id}}")
    except Exception as e:
        logger.error(f"Error processing async inference: {{e}}")

async def start_inference_consumer():
    \"\"\"Background task to consume LLM requests.\"\"\"
    # Wait for Kafka to be ready
    import asyncio
    await asyncio.sleep(10)
    
    bootstrap_servers = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
    
    consumer = AIOKafkaConsumer(
        REQUEST_TOPIC,
        bootstrap_servers=bootstrap_servers,
        group_id="inference-workers",
        auto_offset_reset="earliest"
    )
    
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
    
    try:
        await consumer.start()
        await producer.start()
        logger.info(f"Listening for async inference requests on {{REQUEST_TOPIC}}...")
        
        async for msg in consumer:
            await process_message(producer, msg.value)
    except Exception as e:
        logger.error(f"Inference consumer crashed: {{e}}")
    finally:
        await consumer.stop()
        await producer.stop()
"""
