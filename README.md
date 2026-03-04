# NIKAME

[![CI](https://github.com/omdeepb69/nikame/actions/workflows/ci.yml/badge.svg)](https://github.com/omdeepb69/nikame/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/nikame.svg)](https://badge.fury.io/py/nikame)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Describe your infrastructure. NIKAME builds it.**

NIKAME is a Python-first infrastructure automation framework designed for modern engineering teams. Instead of manually writing thousands of lines of YAML and HCL, you define your high-level architecture in a single `nikame.yaml` file. 

NIKAME handles the rest: generating best-practice Docker Compose files, production-grade Kubernetes manifests (complete with HPA, PDB, and NetworkPolicies), parameterized Helm charts, and cloud-ready Terraform modules.

---

## 🚀 Quick Start

```bash
# Install the CLI
pip install nikame

# Initialize a project using a built-in preset
nikame init --preset saas-starter --output ./my-stack

# Jump in and start services
cd my-stack
nikame up
```

---

## 🛠️ CLI Commands

| Command | Description |
|:---|:---|
| `nikame init` | Initialize a new project from a config file or preset. |
| `nikame up` | Start infrastructure services (Local: Docker Compose, Cloud: Terraform/Helm). |
| `nikame add <module>` | Add a new module (e.g., `postgres`, `qdrant`) to your active config. |
| `nikame remove <mod>` | Safely remove a module and its associated resources. |
| `nikame diff` | Detect drift between your `nikame.yaml` and the generated infra. |
| `nikame regenerate` | Refresh generated files if you've manually edited the YAML config. |
| `nikame ml pull` | Pull production-ready ML models from HuggingFace to your local cache. |
| `nikame github` | Synchronize environment secrets directly to GitHub repository secrets. |
| `nikame destroy` | Tear down all infrastructure and optionally wipe persistent volumes. |
| `nikame login` | Authenticate with NIKAME Hub for community plugins and presets. |

---

## 🌟 What can you build with NIKAME?

### 1. High-Performance SaaS Starter
Generate a full-stack architecture with **FastAPI**, **PostgreSQL** (managed via RDS), **Redis** caching, and **Keycloak** for OIDC authentication. Includes **Stripe** integration skeleton and **Grafana** dashboards for business metrics out of the box.

### 2. RAG (Retrieval-Augmented Generation) Engine
Deploy a production-ready vector search stack. NIKAME will provision **Qdrant**, an **Unstructured** worker for PDF parsing, **vLLM** for local inference, and **Celery** for background embedding jobs — all networked and secured.

### 3. Real-Time Analytics Pipeline
Build an event-driven system using **RedPanda** (Kafka-compatible), **ClickHouse** for OLAP storage, and **Grafana** for real-time visualization. NIKAME configures the consumer groups and storage retention policies automatically.

### 4. Enterprise-Grade API Gateway
Orchestrate **Traefik** or **Nginx** Ingress with automatic **Let's Encrypt** TLS, **Redis-backed rate limiting**, and **OpenTelemetry** tracing for every request across your microservices.

### 5. Multi-Tenant Internal Platform
Create an internal PaaS for your team. Use NIKAME to enforce **ResourceQuotas**, **NetworkPolicies** for namespace isolation, and **Sealed Secrets** for secure GitOps workflows.

---

## 📦 Core Capabilities

- **Compute Optimized**: Automatically selects instance types and resource limits based on your `resource_tier`.
- **Production Hardened**: Generates HPAs, PDBs, and NetworkPolicies by default.
- **Cloud Native**: Supports one-command Terraform generation for **AWS**, **GCP**, and **Azure**.
- **MLOps Ready**: Integrated model management and serving backend selection (Ollama, vLLM, etc.).

---

## 🤝 Maintainer

This project is created and maintained by [@omdeepb69](https://github.com/omdeepb69). Contributions via Pull Requests are always welcome!

---

## License

Apache 2.0
