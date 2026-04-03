"""
RedPanda/Kafka message worker.
"""

import asyncio
import json
from aiokafka import AIOKafkaConsumer
from config import settings

async def start_worker(topic: str, group_id: str):
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=group_id,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8"))
    )
    await consumer.start()
    try:
        async for msg in consumer:
            print(f"Consumed message: {msg.value} from {msg.topic}")
            # Handle message logic here
    finally:
        await consumer.stop()

if __name__ == "__main__":
    # Example usage: python worker.py
    asyncio.run(start_worker("events", "nikame-workers"))
