\"\"\"Elasticsearch async client wrapper.\"\"\"
from elasticsearch import AsyncElasticsearch
from config import settings

search_client = AsyncElasticsearch(settings.ELASTICSEARCH_URL)
