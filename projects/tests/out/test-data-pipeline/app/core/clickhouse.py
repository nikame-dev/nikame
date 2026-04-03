"""ClickHouse async client."""
import aiochclient
import aiohttp
from config import settings

import os
from tenacity import retry, stop_after_attempt, wait_exponential, before_log
import logging

logger = logging.getLogger(__name__)
MAX_RETRIES = int(os.getenv('MAX_RETRY_ATTEMPTS', '3'))

class ClickHouseClient:
    async def get_client(self):
        session = aiohttp.ClientSession()
        return aiochclient.ChClient(session, url=settings.CLICKHOUSE_URL)

clickhouse_client = ClickHouseClient()