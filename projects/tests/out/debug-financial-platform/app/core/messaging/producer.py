"""
RedPanda/Kafka message producer.
"""

import json
from aiokafka import AIOKafkaProducer
from config import settings

async def get_producer():
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    await producer.start()
    return producer

async def send_message(topic: str, message: dict):
    producer = await get_producer()
    try:
        await producer.send_and_wait(topic, message)
    finally:
        await producer.stop()
