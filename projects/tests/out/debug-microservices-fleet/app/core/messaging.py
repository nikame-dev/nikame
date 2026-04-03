"""
Kafka/RedPanda messaging service.
"""

import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from config import settings
import json
import asyncio

logger = logging.getLogger(__name__)

class MessagingService:
    def __init__(self, bootstrap_servers: str):
        self._bootstrap_servers = bootstrap_servers
        self._producer = None
        self._consumers = []

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self._producer.start()

    async def stop(self):
        if self._producer:
            await self._producer.stop()
        for c in self._consumers:
            await c.stop()

    async def send_message(self, topic: str, message: dict):
        logger.info(f"Publishing to {topic}: {message}")
        try:
            await self._producer.send_and_wait(topic, message)
        except Exception as e:
            logger.error(f"Failed to send to {topic}: {e}. Sending to DLQ.")
            await self._send_dlq(topic, message, str(e))

    async def _send_dlq(self, original_topic: str, message: dict, error: str):
        dlq_topic = f"{original_topic}_dlq"
        dlq_message = {"original_message": message, "error": error}
        try:
            await self._producer.send_and_wait(dlq_topic, dlq_message)
        except Exception as dlq_err:
            logger.critical(f"DLQ delivery failed for {dlq_topic}: {dlq_err}")

    async def consume(self, topic: str, group_id: str, callback):
        """Start a consumer for a specific topic."""
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await consumer.start()
        self._consumers.append(consumer)
        
        asyncio.create_task(self._consume_loop(consumer, topic, callback))

    async def _consume_loop(self, consumer, topic, callback):
        try:
            async for msg in consumer:
                try:
                    await callback(msg.value)
                except Exception as e:
                    logger.error(f"Error processing message from {topic}: {e}")
                    await self._send_dlq(topic, msg.value, str(e))
        except Exception as e:
            logger.error(f"Consumer loop failed for {topic}: {e}")

kafka_service = MessagingService(settings.KAFKA_BOOTSTRAP_SERVERS)
