# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig


class VectorSearchCodegen(BaseCodegen):
    NAME = "vector_search"
    DESCRIPTION = "Semantic vector search (Qdrant + sentence-transformers)"
    TRIGGER_MODULES = ["fastapi", "qdrant"]

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx, config)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "vector_search"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        active_modules = self.ctx.active_modules
        vdb = "qdrant"
        if "weaviate" in active_modules: vdb = "weaviate"
        elif "milvus" in active_modules: vdb = "milvus"
        elif "chroma" in active_modules: vdb = "chroma"
        elif "pgvector" in active_modules: vdb = "pgvector"

        files = [
            ("app/services/vector_db.py", self._get_vector_service_py(vdb)),
            ("app/services/__init__.py", ""),
            ("app/search/vector.py", self.env.get_template("vector.py.j2").render()),
        ]
        return files

    def _get_vector_service_py(self, vdb: str) -> str:
        class_name = {
            "qdrant": "QdrantService",
            "weaviate": "WeaviateService",
            "milvus": "MilvusService",
            "chroma": "ChromaService",
            "pgvector": "PostgresService"
        }.get(vdb, "VectorService")
        
        return f'''"""
NIKAME Vector DB Service.
Unified interface for semantic vector operations.
"""
import os
import uuid
from typing import List, Dict, Any

class {class_name}:
    """Singleton service for vector database interactions."""
    
    @classmethod
    async def create_collection(cls, name: str, vector_size: int):
        """Ensure collection exists."""
        pass

    @classmethod
    async def upsert(cls, collection: str, points: List[Dict[str, Any]]):
        """Insert or update vectors."""
        pass

    @classmethod
    async def search(cls, collection: str, vector: List[float], limit: int = 3):
        """Search for similar vectors."""
        return []
'''

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            requirements=["qdrant-client>=1.8.0", "sentence-transformers>=2.5.0"]
        )
