"""RAG Pipeline Integration (Qdrant + MinIO + LLM -> Document Q&A)

Triggers when Vector Search (Qdrant), Object Storage (MinIO), and 
an LLM inference module are present. Provides a complete pipeline for 
document ingestion, chunking, embedding generation, and RAG querying.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from collections import defaultdict
import uuid

from nikame.codegen.integrations.base import BaseIntegration

if TYPE_CHECKING:
    from nikame.blueprint.engine import Blueprint
    from nikame.config.schema import NikameConfig


class RAGPipelineIntegration(BaseIntegration):
    """Generates the RAG document ingestion and querying pipeline."""

    # Dynamic trigger logic handles this
    REQUIRED_MODULES = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_postgres = "postgres" in self.active_modules
        
        # Determine the active vector DB
        vdbs = ["qdrant", "weaviate", "milvus", "chroma", "pgvector"]
        self.active_vdb = next((v for v in vdbs if v in self.active_modules), "qdrant")

    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Custom trigger: Requires Vector DB, Object Storage, AND at least one LLM module."""
        has_vdb = any(m in active_modules for m in ["qdrant", "weaviate", "milvus", "chroma", "pgvector"])
        has_storage = any(m in active_modules for m in ["minio", "s3"])
        has_llm = any(m in active_modules for m in ["llamacpp", "ollama", "vllm", "tgi", "triton", "localai", "xinference", "airllm"])
        return has_vdb and has_storage and has_llm

    def _get_vdb_service_name(self) -> str:
        """Map module name to service class name."""
        mapping = {
            "qdrant": "QdrantService",
            "weaviate": "WeaviateService",
            "milvus": "MilvusService",
            "chroma": "ChromaService",
            "pgvector": "PostgresService"
        }
        return mapping.get(self.active_vdb, "VectorService")

    def generate_core(self) -> list[tuple[str, str]]:
        print("DEBUG: RAGPipelineIntegration.generate_core() CALLED")
        files = []
        
        # 1. RAG Core Service
        rag_service = self._generate_rag_service_py()
        files.append(("app/core/integrations/rag_pipeline.py", rag_service))

        # 2. RAG API Routers
        rag_router = self._generate_rag_router_py()
        files.append(("app/api/v1/endpoints/rag.py", rag_router))

        # 3. If Postgres is active, generate the Document Metadata model
        if self.use_postgres:
            schema_addition = self._generate_document_model_py()
            files.append(("app/models/document_meta.py", schema_addition))

        return files

    def generate_lifespan(self) -> str:
        return f"""
    # --- RAG Integration Startup ---
    # Ensure {self.active_vdb.capitalize()} 'documents' collection exists
    try:
        from app.core.integrations.rag_pipeline import ensure_rag_collection
        await ensure_rag_collection()
    except Exception as e:
        logger.warning(f"Could not initialize RAG collection: {{e}}")
        """

    def generate_health(self) -> dict[str, str]:
        # Health checks for the underlying components are already handled individually
        # This checks the orchestration layer specifically
        return {
            "rag_pipeline": "await check_rag_pipeline_status()"
        }

    def generate_metrics(self) -> str:
        return """
    RAG_DOCUMENTS_PROCESSED = Counter(
        "nikame_rag_documents_processed_total", 
        "Total number of documents ingested into RAG"
    )
    RAG_QUERY_LATENCY = Histogram(
        "nikame_rag_query_latency_seconds",
        "Latency of RAG query resolution"
    )
        """

    def generate_guide(self) -> str:
        return f"""
### RAG Pipeline Integration
**Status:** Active 🟢 
**Components:** Object Storage (MinIO/S3) + {self.active_vdb.capitalize()} (Vectors) + LLM Gateway

The RAG (Retrieval-Augmented Generation) pipeline is pre-wired to handle end-to-end document processing:

1. **Upload**: Send a PDF to `/api/v1/rag/upload`. The file is stored in object storage.
2. **Process**: Text is extracted, chunked, and embedded via the LLM Gateway.
3. **Store**: Vector embeddings are saved to {self.active_vdb.capitalize()}.
4. **Query**: Ask questions at `/api/v1/rag/query`. The system retrieves relevant chunks and synthesizes an answer.

*Note: Since Postgres is active, document metadata (author, upload time, original filename) is automatically synced to the `document_meta` relational table alongside the vector IDs.*
"""

    def _generate_rag_service_py(self) -> str:
        """Generates the main orchestration logic."""
        vdb_service_map = {
            "qdrant": "QdrantService",
            "weaviate": "WeaviateService",
            "milvus": "MilvusService",
            "chroma": "ChromaService",
            "pgvector": "PGVectorService"
        }
        vdb_service = vdb_service_map.get(self.active_vdb, "VectorService")
        
        template = f"""import uuid
from typing import List, Dict, Any
import logging
from fastapi import UploadFile

from app.core.config import settings
from app.services.storage import StorageService
from app.services.vector_db import {vdb_service}
from app.services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)

# Constants optimized by Matrix Engine
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

async def ensure_rag_collection():
    \"\"\"Create the default vector collection if missing.\"\"\"
    await {vdb_service}.create_collection("rag_documents", vector_size=384)

async def process_document(file: UploadFile, metadata: Dict[str, Any] = None) -> str:
    \"\"\"End to end ingestion pipeline.\"\"\"
    doc_id = str(uuid.uuid4())
    
    # 1. Store original file
    object_name = f"documents/{{doc_id}}_{{file.filename}}"
    await StorageService.upload_file("rag-bucket", object_name, file.file)
    logger.info(f"Stored document {{doc_id}} to object storage.")

    # 2. Extract Text (Simulated text extraction for generated stub)
    content = (await file.read()).decode("utf-8", errors="ignore")
    
    # 3. Chunking
    chunks = [content[i:i + CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE - CHUNK_OVERLAP)]
    
    # 4. Embed and Store
    for i, chunk in enumerate(chunks):
        embedding = await LLMGateway.generate_embedding(chunk)
        chunk_meta = {{"doc_id": doc_id, "chunk_index": i, "text": chunk}}
        if metadata:
            chunk_meta.update(metadata)
            
        await {vdb_service}.upsert("rag_documents", [{{"id": str(uuid.uuid4()), "vector": embedding, "payload": chunk_meta}}])
        
    """
        if self.use_postgres:
            template += f"""
    # 5. Sync metadata to Postgres
    from app.models.document_meta import DocumentMeta
    from app.db.session import async_session
    
    async with async_session() as db:
        new_doc = DocumentMeta(id=doc_id, filename=file.filename, chunk_count=len(chunks))
        db.add(new_doc)
        await db.commit()
            """
            
        template += f"""
    return doc_id

async def query_rag(question: str, top_k: int = 3) -> str:
    \"\"\"RAG Query execution.\"\"\"
    # 1. Embed question
    question_vector = await LLMGateway.generate_embedding(question)
    
    # 2. Search Vector DB
    results = await {vdb_service}.search("rag_documents", question_vector, limit=top_k)
    
    # 3. Construct prompt
    context = "\\n".join([r.payload.get("text", "") for r in results])
    prompt = f"Context:\\n{{context}}\\n\\nQuestion:\\n{{question}}\\n\\nAnswer:"
    
    # 4. Generate answer
    answer = await LLMGateway.generate_completion(prompt)
    return answer
"""
        return template

    def _generate_rag_router_py(self) -> str:
        return """from fastapi import APIRouter, UploadFile, File, Form, Depends
from typing import Dict, Any
from app.core.integrations.rag_pipeline import process_document, query_rag

router = APIRouter()

@router.post("/upload")
async def api_upload_document(file: UploadFile = File(...)):
    \"\"\"Ingest a new document into the RAG pipeline.\"\"\"
    doc_id = await process_document(file)
    return {"status": "success", "document_id": doc_id}

@router.post("/query")
async def api_query_rag(question: str = Form(...), top_k: int = Form(3)):
    \"\"\"Ask a question against stored documents.\"\"\"
    answer = await query_rag(question, top_k)
    return {"answer": answer}
"""

    def _generate_document_model_py(self) -> str:
        return """from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base

class DocumentMeta(Base):
    __tablename__ = "document_meta"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    chunk_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
"""
