from fastapi import APIRouter, UploadFile, File, Form, Depends
from typing import Dict, Any
from app.core.integrations.rag_pipeline import process_document, query_rag

router = APIRouter()

@router.post("/upload")
async def api_upload_document(file: UploadFile = File(...)):
    """Ingest a new document into the RAG pipeline."""
    doc_id = await process_document(file)
    return {"status": "success", "document_id": doc_id}

@router.post("/query")
async def api_query_rag(question: str = Form(...), top_k: int = Form(3)):
    """Ask a question against stored documents."""
    answer = await query_rag(question, top_k)
    return {"answer": answer}
