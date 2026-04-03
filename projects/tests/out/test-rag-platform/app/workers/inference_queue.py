import json
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
        
        logger.info(f"Processing async inference job {job_id}...")
        
        # Dispatch to the active gateway
        result = await LLMGateway.generate_completion(prompt)
        
        # Publish response
        res_payload = json.dumps({"job_id": job_id, "status": "complete", "result": result})
        await producer.send_and_wait(RESPONSE_TOPIC, res_payload.encode("utf-8"))
        
        logger.info(f"Completed job {job_id}")
    except Exception as e:
        logger.error(f"Error processing async inference: {e}")

async def start_inference_consumer():
    """Background task to consume LLM requests."""
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
        logger.info(f"Listening for async inference requests on {REQUEST_TOPIC}...")
        
        async for msg in consumer:
            await process_message(producer, msg.value)
    except Exception as e:
        logger.error(f"Inference consumer crashed: {e}")
    finally:
        await consumer.stop()
        await producer.stop()
