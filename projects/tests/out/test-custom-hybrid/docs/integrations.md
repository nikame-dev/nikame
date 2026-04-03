
### Model Drift Monitoring (Evidently)
**Status:** Active 🟢 
**Target Model:** `ollama`

Prediction inputs and outputs are automatically captured via standard request/response models. Background tasks forward this telemetry to the `Evidently` tracking server without blocking the main event loop.



### MLflow Artifact Storage Setup
**Status:** Active 🟢 
**Artifact Backend:** `minio`

MLflow is natively tracking metadata in Postgres and resolving artifact payloads (models, plots) against the locally deployed Object Storage. 



### ML Training Orchestration (Prefect + MLflow)
**Status:** Active 🟢 
**Pipeline Engine:** `prefect`

A fully wired example training pipeline is generated for your selected orchestrator. The pipeline automatically logs parameters, metrics, and models to the local `MLflow` backend tracking server.


### multi_tenancy
Org-based data isolation (Multi-tenancy)


### stripe
Stripe subscription billing and webhook integration
