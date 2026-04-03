import json
import logging
from typing import Any, Dict

from app.services.messaging import RedPandaService
from app.services.search import ElasticsearchService

logger = logging.getLogger(__name__)

# Search Sync Topic (Partitions determined by OptimizationProfile)
SYNC_TOPIC = "search.indexer.commands"

async def publish_search_sync_event(entity_type: str, entity_id: str, action: str, data: Dict[str, Any]):
    """Publish a CDC-like event to RedPanda to trigger indexing."""
    payload = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action, # 'index', 'delete'
        "data": data
    }
    # Publish to topic, sharding by entity_id to guarantee order-of-events per entity
    await RedPandaService.produce(SYNC_TOPIC, key=entity_id, value=json.dumps(payload))
    logger.debug(f"Published search sync event for {entity_type} {entity_id}")

async def start_sync_consumers():
    """Hook into lifecycle to boot up RedPanda topic consumption."""
    await RedPandaService.consume(SYNC_TOPIC, _handle_sync_event)
    logger.info("Search Sync consumers started.")

async def _handle_sync_event(message: bytes):
    """Process the incoming Kafka event."""
    try:
        payload = json.loads(message)
    except Exception as e:
        logger.error(f"Failed to decode sync event: {e}")
        # Prometheus metric: INDEXING_ERRORS.inc()
        return


    # 1. Process inline since no distributed worker queue is active
    await _execute_indexing(payload)


async def _execute_indexing(payload: Dict[str, Any]):
    """Perform the actual Elasticsearch operations."""
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
