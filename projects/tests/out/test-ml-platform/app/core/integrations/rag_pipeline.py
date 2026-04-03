import uuid
from typing import List, Dict, Any
import logging
from fastapi import UploadFile

from core.config import settings
from services.storage import StorageService
from services.vector_db import QdrantService
from services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)

# Constants optimized by Matrix Engine
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

async def ensure_rag_collection():
    """Create the default vector collection if missing."""
    await QdrantService.create_collection("rag_documents", vector_size=384)

async def process_document(file: UploadFile, metadata: Dict[str, Any] = None) -> str:
    """End to end ingestion pipeline."""
    doc_id = str(uuid.uuid4())
    
    # 1. Store original file
    object_name = f"documents/{doc_id}_{file.filename}"
    await StorageService.upload_file("rag-bucket", object_name, file.file)
    logger.info(f"Stored document {doc_id} to object storage.")

    # 2. Extract Text (Simulated text extraction for generated stub)
    content = (await file.read()).decode("utf-8", errors="ignore")
    
    # 3. Chunking
    chunks = [content[i:i + CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE - CHUNK_OVERLAP)]
    
    # 4. Embed and Store
    for i, chunk in enumerate(chunks):
        embedding = await LLMGateway.generate_embedding(chunk)
        chunk_meta = {"doc_id": doc_id, "chunk_index": i, "text": chunk}
        if metadata:
            chunk_meta.update(metadata)
            
        await QdrantService.upsert("rag_documents", [{"id": str(uuid.uuid4()), "vector": embedding, "payload": chunk_meta}])
        
    
    # 5. Sync metadata to Postgres
    from models.document_meta import DocumentMeta
    from db.session import async_session
    
    async with async_session() as db:
        new_doc = DocumentMeta(id=doc_id, filename=file.filename, chunk_count=len(chunks))
        db.add(new_doc)
        await db.commit()
            
    return doc_id

async def query_rag(question: str, top_k: int = 3) -> str:
    """RAG Query execution."""
    # 1. Embed question
    question_vector = await LLMGateway.generate_embedding(question)
    
    # 2. Search Vector DB
    results = await QdrantService.search("rag_documents", question_vector, limit=top_k)
    
    # 3. Construct prompt
    context = "\n".join([r.payload.get("text", "") for r in results])
    prompt = f"Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer:"
    
    # 4. Generate answer
    answer = await LLMGateway.generate_completion(prompt)
    return answer
