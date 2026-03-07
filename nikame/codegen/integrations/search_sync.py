"""Event-Driven Search Sync Integration

Triggers when Elasticsearch, RedPanda, and Postgres are active.
Implements the CQRS pattern where Postgres modifications emit CDC events
to RedPanda, which are then asynchronously consumed and indexed into 
Elasticsearch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from collections import defaultdict

from nikame.codegen.integrations.base import BaseIntegration

if TYPE_CHECKING:
    from nikame.blueprint.engine import Blueprint
    from nikame.config.schema import NikameConfig


class SearchSyncIntegration(BaseIntegration):
    """Generates the asynchronous search pipeline via RedPanda."""

    REQUIRED_MODULES = ["elasticsearch", "redpanda", "postgres"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if Celery is present to dispatch to workers instead of inline consumers
        self.use_celery = "celery" in self.active_modules

    def generate_core(self) -> list[tuple[str, str]]:
        files = []
        sync_service = self._generate_sync_service_py()
        files.append(("app/core/integrations/search_sync.py", sync_service))
        return files

    def generate_lifespan(self) -> str:
        return """
    # --- Search Sync Integration Startup ---
    # Register Kafka Consumers for Elasticsearch syncing
    from app.core.integrations.search_sync import start_sync_consumers
    await start_sync_consumers()
        """

    def generate_health(self) -> dict[str, str]:
        return {
            "search_sync_lag": "await check_sync_consumer_lag()"
        }

    def generate_metrics(self) -> str:
        return """
    DOCUMENTS_INDEXED = Counter("nikame_search_documents_indexed_total", "Total documents synced to Elasticsearch")
    INDEXING_ERRORS = Counter("nikame_search_indexing_errors_total", "Errors during event-driven indexing")
        """

    def generate_guide(self) -> str:
        guide = """
### Event-Driven Search Sync
**Status:** Active 🟢
**Components:** Postgres -> RedPanda -> Elasticsearch

The Matrix Engine detected your CQRS architecture. Instead of dual-writing to the database and search engine synchronously (which causes latency and reliability issues), changes are streamed through RedPanda:

1. Insert data to Postgres.
2. Publish `entity.created` event to RedPanda via `publish_search_sync_event(entity)`.
3. An asynchronous consumer picks up the event and indexes it into Elasticsearch.
"""
        if self.use_celery:
            guide += "\n*Because Celery is active, the RedPanda consumer does not process the document inline! It immediately dispatches the payload to a Celery background worker, ensuring the highest performance event ingestion.*"
            
        return guide

    def _generate_sync_service_py(self) -> str:
        template = f"""import json
import logging
from typing import Any, Dict

from app.services.messaging import RedPandaService
from app.services.search import ElasticsearchService

logger = logging.getLogger(__name__)

# Search Sync Topic (Partitions determined by OptimizationProfile)
SYNC_TOPIC = "search.indexer.commands"

async def publish_search_sync_event(entity_type: str, entity_id: str, action: str, data: Dict[str, Any]):
    \"\"\"Publish a CDC-like event to RedPanda to trigger indexing.\"\"\"
    payload = {{
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action, # 'index', 'delete'
        "data": data
    }}
    # Publish to topic, sharding by entity_id to guarantee order-of-events per entity
    await RedPandaService.produce(SYNC_TOPIC, key=entity_id, value=json.dumps(payload))
    logger.debug(f"Published search sync event for {{entity_type}} {{entity_id}}")

async def start_sync_consumers():
    \"\"\"Hook into lifecycle to boot up RedPanda topic consumption.\"\"\"
    await RedPandaService.consume(SYNC_TOPIC, _handle_sync_event)
    logger.info("Search Sync consumers started.")

async def _handle_sync_event(message: bytes):
    \"\"\"Process the incoming Kafka event.\"\"\"
    try:
        payload = json.loads(message)
    except Exception as e:
        logger.error(f"Failed to decode sync event: {{e}}")
        # Prometheus metric: INDEXING_ERRORS.inc()
        return

"""
        if self.use_celery:
            template += """
    # 1. Dispatch to Celery worker immediately for offloaded processing
    from app.worker import process_search_index_task
    process_search_index_task.delay(payload)
    logger.debug(f"Dispatched sync task to Celery for {payload.get('entity_id')}")
"""
        else:
            template += """
    # 1. Process inline since no distributed worker queue is active
    await _execute_indexing(payload)
"""     

        template += """

async def _execute_indexing(payload: Dict[str, Any]):
    \"\"\"Perform the actual Elasticsearch operations.\"\"\"
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")
    action = payload.get("action")
    data = payload.get("data")
    
    index_name = f"nikame_{entity_type}s"
    
    try:
        if action == "delete":
            await ElasticsearchService.delete(index_name, entity_id)
            logger.info(f"Deleted {entity_id} from Elasticsearch")
        else:
            await ElasticsearchService.index(index_name, entity_id, data)
            # Prometheus metric: DOCUMENTS_INDEXED.inc()
            logger.info(f"Indexed {entity_id} into Elasticsearch")
    except Exception as e:
        logger.error(f"Search indexing failed: {e}")
        # Prometheus metric: INDEXING_ERRORS.inc()
        raise e # Let Kafka retry mechanisms (or DLQ) handle failure

# async def check_sync_consumer_lag() -> str:
#    # Implement Kafka partition lag checking
#    pass
"""
        return template
