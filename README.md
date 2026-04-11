# 🛸 NIKAME: The Autonomous Systems Orchestrator

**NIKAME** is a state-aware, agentic development ecosystem designed to bridge the gap between infrastructure orchestration and high-fidelity code scaffolding. It doesn't just generate boilerplate; it architects production-grade, async-first environments and maintains them through an autonomous "Analyze → Audit → Execute → Verify" loop.

Built for the "Day 2" challenges of engineering, NIKAME ensures that your infrastructure, database schemas, and application logic remain in perfect harmony as you scale from a single service to a complex distributed system.

---

## 🚀 Core Philosophy

NIKAME is built on four non-negotiable pillars of modern engineering:
- **Clean Architecture**: Strict separation of Entities, Use Cases, and Adapters.
- **Async-First**: Native support for high-concurrency Python (FastAPI/AnyIO).
- **Infrastructure-as-Code**: Single-source-of-truth orchestration via `nikame.yaml`.
- **Agentic Automation**: Local-first AI that understands the *state* of your project.

---

## 🏗️ The Powerhouse Features

### 🧠 Stateful Awareness Engine
NIKAME operates with a persistent memory via the `.nikame_context` manifest. The NIKAME Copilot "remembers" every pattern injected, service port allocated, and migration applied, ensuring that every new action is contextually aware of what has already been built.

### 🛡️ Integrity Engine
The "Self-Healing" heart of NIKAME. 
- **Port Negotiation**: Automatically detects and resolves port collisions (e.g., managing multiple Redis DB indices for Celery vs. Rate Limiters).
- **Smoke Testing**: Every automated write is followed by an isolated subprocess initialization test. If a circular import or syntax error is detected, the engine performs a **Zero-Downtime Rollback** using `.bak` snapshots.

### ⚡ AST-Aware Glue Logic
Unlike generic LLM tools that bloat your context, NIKAME uses **AST Stubbing**. The agent "sees" your project through high-density stubs (metadata & signatures) instead of raw source code. This allows local models (like `qwen2.5-coder`) to perform surgical code injections with lightning speed and 99% accuracy.

### 📦 Production Pattern Registry
Access a curated library of 100+ production patterns including JWT Auth, Google OAuth2, Celery-Redis Task Queues, and Sliding-Window Rate Limiters—all pre-configured for NIKAME's vertical-slice architecture.

---

## 🤖 The Agentic Workflow

The **NIKAME Copilot** isn't just a chatbot; it's a member of your team with write access to your filesystem.

1.  **Analyze**: Uses the Project Scanner and `.nikame_context` to understand your current stack.
2.  **Audit**: Cross-references requirements against the `Integrity Engine` (Resource + Syntax check).
3.  **Execute**: Proposes a Plan of Action and executes surgical `[WRITE]` or `[SCAFFOLD]` actions.
4.  **Verify**: Runs a post-execution Smoke Test to ensure the system remains Green.

---

## 🛠️ CLI Command Reference

| Command | Action | Description |
| :--- | :--- | :--- |
| `nikame init` | **Initialize** | Bootstrap infrastructure (Docker/K8s) from a config or preset. |
| `nikame copilot` | **Collaborate** | Launch the context-aware, local-first AI assistant. |
| `nikame agent` | **Automate** | Launch an autonomous mission (e.g., "Build the Projects domain"). |
| `nikame scaffold add` | **Inject** | Surgical injection of a production pattern into your codebase. |
| `nikame verify` | **Integrity** | Run global health checks and environment-wide Smoke Tests. |
| `nikame up` | **Provision** | Start infrastructure services and local development proxies. |
| `nikame info` | **Metadata** | Inspect pattern manifests, dependencies, and file mappings. |

---

## ⚡ Technical Showcase: KV-Cache Optimization

NIKAME is optimized for **Local-First AI**. By implementing Selective Retrieval and AST-based stubbing, we reduce the token pressure on local models by up to 80%. This means you can run professional-grade architectural refactoring on your local machine (/home/omdeep-borkar/) with absolute privacy and zero latency.

### Example Usage:
```bash
# Initialize your project
nikame init --config my-app.yaml

# Collaborative Building
nikame copilot
>>> "Add Google Auth and ensure it doesn't conflict with my existing User model."

# The Copilot:
# 1. Scans app/api/auth/models.py
# 2. Identifies 'User' class exists
# 3. Proposes an aliased integration or merge
# 4. Executes and runs Smoke Test automatically.
```

---

## 🔐 Local-First Advantage
All code, project context, and LLM reasoning stay entirely on your local machine. By leveraging **Ollama**, NIKAME ensures that your proprietary architecture never leaves your workspace.

**NIKAME: From Zero to Production-Ready, Guided by Local Intelligence.**

---
© 2026 NIKAME Framework // Autonomous Systems Engineering
