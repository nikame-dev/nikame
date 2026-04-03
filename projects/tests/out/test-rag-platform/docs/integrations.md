
### Agent Framework (langchain)
**Status:** Active 🟢 
**Wiring:** 
- **LLM Engine:** `ollama`
- **Vector Store:** `qdrant`

The agent executor is automatically configured to use your self-hosted LLM and Vector search. 
Import `get_agent_executor` from `app.core.integrations.agent_framework` to kick off AI tasks natively in your route handlers.



### Asynchronous Inference Queue (RedPanda)
**Status:** Active 🟢 
**Target Engine:** `ollama`

Large requests to `ollama` can be slow. Since RedPanda is active, an asynchronous request/reply message broker has been auto-configured.

1. Publish generation requests to the `inference.requests` Kafka topic.
2. The `app.workers.inference_queue` consumer picks them up, processes them against the LLM, and publishes the result to the `inference.responses` topic.



### Cache-Aside Integration
**Status:** Active 🟢
**Components:** Postgres + Dragonfly
**Tuning:** TTL set to 3600s (optimized for balanced)

The Matrix Engine has automatically injected a cache-aside layer. Wrap any expensive database repository calls with `@cache_query(prefix="users")`.



### Event Idempotency Integration
**Status:** Active 🟢
**Components:** RedPanda + Dragonfly
**Tuning:** ID Tracking TTL set to 7200s

The Matrix Engine has automatically injected an Exactly-Once processing layer. Wrap any Kafka consumer functions with `@idempotent_consumer`. The system will automatically check Dragonfly for the Message ID before processing and drop duplicates.



### MLflow Artifact Storage Setup
**Status:** Active 🟢 
**Artifact Backend:** `minio`

MLflow is natively tracking metadata in Postgres and resolving artifact payloads (models, plots) against the locally deployed Object Storage. 



### ML Training Orchestration (Prefect + MLflow)
**Status:** Active 🟢 
**Pipeline Engine:** `prefect`

A fully wired example training pipeline is generated for your selected orchestrator. The pipeline automatically logs parameters, metrics, and models to the local `MLflow` backend tracking server.



### Transactional Outbox Pattern
**Status:** Active 🟢
**Components:** Postgres + RedPanda

When building distributed systems, updating a database and publishing an event (dual-write) can lead to inconsistencies if the system crashes midway. The Matrix Engine has added the Transactional Outbox Pattern to fix this:

1. In your `async_session`, save business models AND `OutboxEvent` models in the exact same transaction.
2. A background process sweeps the Outbox table for unpublished events and guarantees delivery to RedPanda 'at-least-once'.



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


### vector_search
Semantic vector search (Qdrant + sentence-transformers)


### multi_tenancy
Org-based data isolation (Multi-tenancy)


### stripe
Stripe subscription billing and webhook integration
