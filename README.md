# NIKAME

[![CI](https://github.com/nikame-dev/nikame/actions/workflows/ci.yml/badge.svg)](https://github.com/nikame-dev/nikame/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/nikame.svg)](https://badge.fury.io/py/nikame)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Versions](https://img.shields.io/pypi/pyversions/nikame.svg)](https://pypi.org/project/nikame/)

**Describe your infrastructure. NIKAME builds the glue.**

NIKAME is the intelligent infrastructure framework that understands how your modules should work together. Unlike traditional scaffolding tools that just spit out template files, NIKAME features the **Matrix Engine**—a central intelligence layer that detects module combinations and automatically generates the complex "glue code" required for production-grade integrations.

---

## 🚀 Why NIKAME?

Manual infrastructure wiring is error-prone and tedious. NIKAME solves this by providing:

- **Intelligent Matrix Engine**: Detects active modules and automatically injects integration layers (e.g., if you have `Postgres` and `Redpanda`, it automatically adds the **Transactional Outbox Pattern**).
- **Production-Grade by Default**: Generates Kubernetes manifests with HPAs, PDBs, NetworkPolicies, and ResourceQuotas.
- **Smart Stacks**: Pre-optimized blueprints for RAG, SaaS, Event-Driven, and Real-time Analytics.
- **Cloud Native**: One-command Terraform and Helm generation for AWS, GCP, and Azure.

---

## 🛠️ CLI Commands

| Command | Description |
|:---|:---|
| `nikame init` | Initialize a new project from a config file or preset. |
| `nikame up` | Start local services using Docker Compose. |
| `nikame down` | Stop local services and clean up. |
| `nikame add <mod>` | Add a new module (e.g., `qdrant`, `valkey`) to your active config. |
| `nikame remove <mod>`| Safely remove a module and its associated resources. |
| `nikame regenerate` | Refresh generated files after manual YAML edits. |
| `nikame diff` | Detect drift between your `nikame.yaml` and generated infra. |
| `nikame ml pull` | Pull production-ready ML models from HuggingFace to local cache. |
| `nikame github` | Synchronize environment secrets directly to GitHub repository secrets. |
| `nikame tunnel` | Expose local services to the internet via ngrok for testing. |

---

## 🌟 Intelligent "Matrix" Integrations

NIKAME doesn't just provision services; it wires them. Here are some of the **10+ automatic integrations** the Matrix Engine handles:

- **RAG Pipeline**: Wires `vLLM` + `Qdrant` + `MinIO` into a production-ready API.
- **Transactional Outbox**: Guarantees event delivery between `Postgres` and `Redpanda`.
- **Search Sync**: Real-time synchronization between `PostgreSQL` and `Elasticsearch`.
- **Cache-Aside**: Pre-wired caching logic between `FastAPI` and `Redis/Dragonfly`.
- **Auth Proxy**: Seamless OIDC integration between `Keycloak` and your API services.
- **Distributed Tracing**: Automatic propagation through `OpenTelemetry` across all services.

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

## 🤝 Maintainer

This project is created and maintained by [@omdeepb69](https://github.com/omdeepb69).

---

## License

Apache 2.0
