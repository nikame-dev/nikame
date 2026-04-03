
### MLflow Artifact Storage Setup
**Status:** Active 🟢 
**Artifact Backend:** `minio`

MLflow is natively tracking metadata in Postgres and resolving artifact payloads (models, plots) against the locally deployed Object Storage. 



### ML Training Orchestration (Prefect + MLflow)
**Status:** Active 🟢 
**Pipeline Engine:** `prefect`

A fully wired example training pipeline is generated for your selected orchestrator. The pipeline automatically logs parameters, metrics, and models to the local `MLflow` backend tracking server.



### RAG Pipeline Integration
**Status:** Active 🟢 
**Components:** Object Storage (MinIO/S3) + Qdrant (Vectors) + LLM Gateway

The RAG (Retrieval-Augmented Generation) pipeline is pre-wired to handle end-to-end document processing:

1. **Upload**: Send a PDF to `/api/v1/rag/upload`. The file is stored in object storage.
2. **Process**: Text is extracted, chunked, and embedded via the LLM Gateway.
3. **Store**: Vector embeddings are saved to Qdrant.
4. **Query**: Ask questions at `/api/v1/rag/query`. The system retrieves relevant chunks and synthesizes an answer.

*Note: Since Postgres is active, document metadata (author, upload time, original filename) is automatically synced to the `document_meta` relational table alongside the vector IDs.*



### Distributed Tracing (OpenTelemetry)
**Status:** Active 🟢
**Components:** OpenTelemetry Collector / Tempo

A context propagator has been wired directly into the FastApi `lifespan`. This intercepts incoming HTTP requests, intercepts downstream database queries, and intercepts outgoing event messages. This guarantees full end-to-end trace visibility in Tempo/Grafana without manual span tracking in every router.



### LLM Tracing (LangFuse)
**Status:** Active 🟢 
**Target Engine:** `vllm`

All calls to the LLM Gateway are instrumented with OpenTelemetry and LangFuse native callbacks to log prompts, responses, token usage, and latency. 
