
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



### Distributed Tracing (OpenTelemetry)
**Status:** Active 🟢
**Components:** OpenTelemetry Collector / Tempo

A context propagator has been wired directly into the FastApi `lifespan`. This intercepts incoming HTTP requests, intercepts downstream database queries, and intercepts outgoing event messages. This guarantees full end-to-end trace visibility in Tempo/Grafana without manual span tracking in every router.


### multi_tenancy
Org-based data isolation (Multi-tenancy)


### stripe
Stripe subscription billing and webhook integration
