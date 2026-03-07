
### RAG Pipeline Integration
**Status:** Active 🟢 
**Components:** MinIO (Documents) + Qdrant (Vectors) + LLM Gateway

The RAG (Retrieval-Augmented Generation) pipeline is pre-wired to handle end-to-end document processing:

1. **Upload**: Send a PDF to `/api/v1/rag/upload`. The file is stored in MinIO.
2. **Process**: Text is extracted, chunked, and embedded via the LLM Gateway.
3. **Store**: Vector embeddings are saved to Qdrant.
4. **Query**: Ask questions at `/api/v1/rag/query`. The system retrieves relevant chunks and synthesizes an answer.

*Note: Since Postgres is active, document metadata (author, upload time, original filename) is automatically synced to the `document_meta` relational table alongside the vector IDs.*
