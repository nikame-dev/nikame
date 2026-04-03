"""Qdrant vector search client."""
from qdrant_client import AsyncQdrantClient
from config import settings

vector_client = AsyncQdrantClient(url=settings.QDRANT_URL)
