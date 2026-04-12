# NIKAME — Full Roadmap to 100/100
### The Antogravity Build Spec

> **Mission:** Transform NIKAME from an ambitious prototype into the definitive FastAPI scaffolding and agentic development platform. Think `shadcn/ui` meets `opencode` meets `railway.app` — but for backend engineers who want full control.
>
> **Target:** A tool that senior engineers at Anthropic, Google, and Stripe would willingly use and recommend.

---

## 0. North Star Vision

```
nikame init          →  validated, typed, beautiful TUI wizard
nikame add auth.jwt  →  live diff preview → confirm → inject → verify → done in 4 seconds
nikame agent         →  full opencode-style TUI: file tree, diff view, LLM stream, rollback
nikame verify        →  pure static analysis, cycle detection, type graph, zero subprocess
nikame publish       →  your own pattern to the public registry
```

NIKAME is the tool that makes starting a FastAPI project feel like using Vercel — except you own every byte and it works offline.

---

## PHASE 0 — Emergency Triage
**Timeline: Day 1. No exceptions.**
**Goal: Stop the bleeding. Every item here actively hurts the project's reputation.**

### 0.1 Repo Hygiene

- [ ] Delete `tmp/` directory from repo entirely
- [ ] Add to `.gitignore`: `tmp/`, `projects/`, `*.log`, `.nikame_context.local`, `__pycache__/`, `.pytest_cache/`, `dist/`, `*.egg-info/`
- [ ] Rename `example_scenaios/` → `examples/` (merge with any existing `examples/` dir, delete duplicate)
- [ ] Remove `/home/omdeep-borkar/` from `README.md` — every occurrence
- [ ] Fix `CONTRIBUTING.md` clone URL → `https://github.com/nikame-dev/nikame.git`
- [ ] Move `auto_wire.py` from root to `examples/demos/auto_wire_demo.py` with a top-of-file docstring explaining it's a usage demo
- [ ] Move `verify_prod.yaml` from root to `examples/configs/verify_prod.yaml`
- [ ] Add proper `.gitattributes` for line ending normalization
- [ ] Audit all other root-level files — nothing that isn't `pyproject.toml`, `README.md`, `CHANGELOG.md`, `LICENSE`, `CONTRIBUTING.md`, `Makefile` should live at root

### 0.2 Linting / Type Config

- [ ] Remove `F401` from ruff `ignore` list — fix all unused imports instead
- [ ] Remove `S603`, `S607` suppression — fix the underlying subprocess calls with proper validation
- [ ] Remove `S701` (Jinja2 autoescape) suppression — enable autoescape on all template envs with `autoescape=True` and use `select_autoescape()`
- [ ] Ensure `mypy --strict` passes with zero errors before any new code is written
- [ ] Add `ruff format` as a pre-commit hook
- [ ] Add `pyright` as secondary type checker for LSP compatibility

### 0.3 CHANGELOG

- [ ] Create `CHANGELOG.md` using [Keep a Changelog](https://keepachangelog.com) format
- [ ] Backfill entries for v1.0.0 through v1.3.1 from git log
- [ ] Every future PR must include a CHANGELOG entry — enforce via CI check

### 0.4 Freeze v1.3.1

- [ ] Tag `v1.3.1-legacy` on the current broken commit for historical reference
- [ ] All new work goes on a `v2-dev` branch. `main` stays frozen until Phase 2 is complete and tested.

---

## PHASE 1 — Core Architecture Refactor
**Timeline: Week 1–2**
**Goal: Establish the architectural contract that everything else builds on. No feature additions yet.**

### 1.1 Package Structure

Enforce strict layered architecture with zero upward imports. This is non-negotiable — CI will enforce it with `import-linter`.

```
nikame/
├── core/                    # KERNEL — zero nikame-internal deps, zero LLM deps
│   ├── config/
│   │   ├── schema.py        # Pydantic v2 NikameConfig, all sub-models
│   │   ├── loader.py        # load + validate nikame.yaml, migration path
│   │   └── migrator.py      # config schema version migrations
│   ├── manifest/
│   │   ├── schema.py        # ManifestV1, ManifestV2 (versioned state)
│   │   ├── store.py         # read/write .nikame_context
│   │   └── migrator.py      # manifest version migrations
│   ├── ast/
│   │   ├── stubber.py       # AST → compact stub repr for LLM context
│   │   ├── graph.py         # import graph builder using networkx
│   │   └── cycle.py         # cycle detector, returns typed results
│   ├── registry/
│   │   ├── loader.py        # loads pattern manifests from registry dir
│   │   ├── resolver.py      # resolves requires/conflicts between patterns
│   │   └── schema.py        # PatternManifest Pydantic model
│   ├── ports.py             # ResourceResolver — port + Redis DB allocation
│   ├── diff.py              # ProjectDiff — what would change, before it changes
│   └── errors.py            # All custom exceptions, typed, exported
│
├── engines/                 # SERVICES — depends on core only
│   ├── scaffold.py          # ScaffoldEngine: template rendering, file injection
│   ├── verify.py            # SyntaxVerifier: static analysis, no subprocess
│   ├── rollback.py          # RollbackEngine: snapshot → restore
│   └── env.py               # EnvEngine: .env generation, secret detection
│
├── copilot/                 # AI LAYER — depends on engines + core
│   ├── providers/
│   │   ├── base.py          # LLMProvider Protocol
│   │   ├── ollama.py
│   │   ├── openai.py
│   │   ├── anthropic.py
│   │   └── groq.py
│   ├── context.py           # ContextManager: stub generation, token budgeting
│   ├── agent.py             # AgentLoop: plan → act → verify → commit
│   └── planner.py           # ActionPlanner: LLM → structured actions
│
├── infra/                   # INFRA LAYER — depends on core only
│   ├── docker.py            # Dockerfile + compose generation
│   ├── kubernetes.py        # Helm chart generation
│   └── providers/
│       ├── aws.py
│       ├── gcp.py
│       └── azure.py
│
├── tui/                     # TERMINAL UI — depends on everything
│   ├── app.py               # Textual App root
│   ├── screens/
│   │   ├── init_wizard.py   # nikame init TUI
│   │   ├── agent.py         # nikame agent full-screen TUI (opencode-style)
│   │   ├── scaffold.py      # nikame add diff + confirm screen
│   │   └── dashboard.py     # project health dashboard
│   ├── components/
│   │   ├── file_tree.py     # live file tree widget
│   │   ├── diff_view.py     # syntax-highlighted diff widget
│   │   ├── llm_stream.py    # streaming LLM output widget
│   │   ├── pattern_picker.py # searchable pattern browser widget
│   │   └── status_bar.py    # progress + spinner widget
│   └── theme.py             # NIKAME color theme, consistent tokens
│
├── cli/                     # CLI SHELL — thin wrappers, zero business logic
│   ├── main.py              # Typer app root, all command registration
│   ├── commands/
│   │   ├── init.py
│   │   ├── add.py
│   │   ├── remove.py
│   │   ├── verify.py
│   │   ├── diff.py
│   │   ├── stub.py
│   │   ├── agent.py
│   │   ├── validate.py
│   │   ├── publish.py
│   │   └── info.py
│   └── output.py            # Rich console, consistent formatting helpers
│
└── registry/                # DATA ONLY — Jinja2 templates + pattern manifests
    └── patterns/
        └── auth/
            └── jwt/
                ├── manifest.yaml
                ├── templates/
                │   ├── router.j2
                │   └── security.j2
                └── tests/
                    └── test_auth.j2
```

### 1.2 Canonical Config Schema

Define once, validate everywhere. This is the contract between users and NIKAME.

```python
# nikame/core/config/schema.py

from pydantic import BaseModel, field_validator
from typing import Literal

class CopilotConfig(BaseModel):
    provider: Literal["ollama", "openai", "anthropic", "groq"] = "ollama"
    model: str = "qwen2.5-coder:7b"
    temperature: float = 0.2
    max_context_tokens: int = 8192

class EnvironmentConfig(BaseModel):
    target: Literal["local", "aws", "gcp", "azure"] = "local"
    resource_tier: Literal["small", "medium", "large"] = "medium"
    domain: str | None = None

class ObservabilityConfig(BaseModel):
    metrics: bool = False
    tracing: bool = False
    logging: Literal["stdout", "loki", "cloudwatch"] = "stdout"

class NikameConfig(BaseModel):
    version: Literal["2.0"] = "2.0"
    name: str
    description: str | None = None
    modules: list[str] = []        # dotted: "database.postgres", "auth.jwt"
    features: list[str] = []       # flat: "rate_limiting", "cron_jobs"
    environment: EnvironmentConfig = EnvironmentConfig()
    copilot: CopilotConfig = CopilotConfig()
    observability: ObservabilityConfig = ObservabilityConfig()

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, v: list[str]) -> list[str]:
        for mod in v:
            if "." not in mod:
                raise ValueError(f"Module '{mod}' must be dotted: e.g. 'database.postgres'")
        return v
```

- [ ] Implement `NikameConfig` and all sub-models with full Pydantic v2 validators
- [ ] Implement `loader.py`: load YAML → validate → return typed `NikameConfig`, raise `ConfigValidationError` with Rich-formatted error message showing the exact field
- [ ] Implement config schema migrations: `v1.x nikame.yaml` → auto-migrated to `v2.0` on load, with user prompt before writing back

### 1.3 Versioned Manifest

```python
# nikame/core/manifest/schema.py

from pydantic import BaseModel
from datetime import datetime

class AppliedPattern(BaseModel):
    id: str                    # "auth.jwt"
    version: str               # "2.1"
    applied_at: datetime
    files_created: list[str]
    files_modified: list[str]
    env_vars_added: list[str]

class AllocatedPort(BaseModel):
    service: str
    port: int
    protocol: Literal["tcp", "udp"] = "tcp"

class ManifestV2(BaseModel):
    manifest_version: Literal["2"] = "2"
    nikame_version: str
    project_name: str
    created_at: datetime
    patterns_applied: list[AppliedPattern] = []
    ports_allocated: list[AllocatedPort] = []
    env_vars: list[str] = []
    last_verified: datetime | None = None
    verification_passed: bool | None = None
```

- [ ] Implement `ManifestV2` and store as `.nikame/context.yaml` (note: move from `.nikame_context` to a hidden `.nikame/` directory to hold state, cache, and snapshots together)
- [ ] Implement `ManifestMigrator` to handle v1 → v2 conversion
- [ ] Implement snapshot system: before any scaffold operation, write `.nikame/snapshots/{timestamp}/` with copies of files to be modified — this is the rollback source of truth

### 1.4 Pattern Registry Schema

Every pattern in the registry must have a `manifest.yaml`. No manifest = not a valid pattern.

```yaml
# nikame-registry/patterns/auth/jwt/manifest.yaml
id: auth.jwt
version: "2.1"
display_name: JWT Authentication
description: Stateless JWT with refresh token rotation and token blacklisting
category: auth
tags: [security, stateless, api]
author: nikame-core

requires:
  - database.postgres      # hard dependency
  - cache.redis            # hard dependency

conflicts:
  - auth.session           # cannot coexist

optional:
  - observability.sentry   # adds error reporting to auth flows

injects:
  - path: app/api/auth/router.py
    template: router.j2
    operation: create       # create | append | patch

  - path: app/core/security.py
    template: security.j2
    operation: create

  - path: app/models/user.py
    template: user_model_patch.j2
    operation: patch        # patch = AST-aware merge, not overwrite
    patch_target: "class User"

migrations:
  - 001_create_token_blacklist.sql

env_vars:
  - name: JWT_SECRET_KEY
    description: Secret key for JWT signing
    example: "your-super-secret-key-here"
    required: true
  - name: JWT_ALGORITHM
    description: JWT signing algorithm
    example: "HS256"
    default: "HS256"
    required: true
  - name: ACCESS_TOKEN_EXPIRE_MINUTES
    default: "30"
    required: false

tests:
  - template: test_auth.j2
    path: tests/api/test_auth.py

docs_url: https://nikame.dev/patterns/auth/jwt
```

- [ ] Implement `PatternManifest` Pydantic model matching the schema above
- [ ] Implement `RegistryLoader`: scan registry directory, validate each manifest on load, cache results
- [ ] Implement `ConflictResolver`: given a set of applied patterns + a new pattern, return `ConflictResult` listing hard conflicts, unmet requirements, and optional suggestions
- [ ] Implement `PatternSearch`: fuzzy name search + tag filtering for the `nikame add` picker

### 1.5 Static Verification Engine

Replace subprocess smoke tests entirely.

```python
# nikame/core/ast/graph.py

import ast
from pathlib import Path
import networkx as nx
from dataclasses import dataclass

@dataclass
class ImportEdge:
    from_module: str
    to_module: str
    line: int
    is_relative: bool

@dataclass
class VerificationResult:
    passed: bool
    cycles: list[list[str]]
    missing_imports: list[str]
    type_errors: list[str]      # from pyright JSON output if available
    duration_ms: float

class ImportGraphBuilder:
    def build(self, root: Path) -> nx.DiGraph:
        """Walk all .py files, parse imports with ast, build directed graph."""
        ...

class CycleDetector:
    def detect(self, graph: nx.DiGraph) -> list[list[str]]:
        """Return all simple cycles using nx.simple_cycles."""
        ...

class SyntaxVerifier:
    def __init__(self, root: Path):
        self.root = root
        self._builder = ImportGraphBuilder()
        self._detector = CycleDetector()

    def verify(self) -> VerificationResult:
        graph = self._builder.build(self.root)
        cycles = self._detector.detect(graph)
        return VerificationResult(
            passed=len(cycles) == 0,
            cycles=cycles,
            missing_imports=self._find_missing(graph),
            type_errors=[],
            duration_ms=...,
        )
```

- [ ] Implement `ImportGraphBuilder` using Python's `ast` module — no execution, no subprocess
- [ ] Implement `CycleDetector` using `nx.simple_cycles`
- [ ] Implement `SyntaxVerifier.verify()` returning `VerificationResult`
- [ ] Expose `nikame verify` command that prints a Rich table of results with cycle paths highlighted
- [ ] Make `nikame verify --watch` re-run on file change using `watchfiles`

### 1.6 AST Stubber

The intellectually interesting part of NIKAME deserves first-class treatment.

```python
# nikame/core/ast/stubber.py

from dataclasses import dataclass, field
import ast

@dataclass
class ParamStub:
    name: str
    annotation: str | None
    default: str | None

@dataclass
class FunctionStub:
    name: str
    params: list[ParamStub]
    return_annotation: str | None
    decorators: list[str]
    docstring: str | None
    is_async: bool

@dataclass
class ClassStub:
    name: str
    bases: list[str]
    methods: list[FunctionStub]
    class_vars: list[tuple[str, str | None]]  # (name, annotation)
    decorators: list[str]

@dataclass
class ModuleStub:
    path: str
    imports: list[str]
    classes: list[ClassStub]
    functions: list[FunctionStub]
    global_vars: list[tuple[str, str | None]]

    def to_compact_repr(self) -> str:
        """
        Serialize to a compact pseudo-Python representation.
        Drops all implementation details, keeps shape + types.
        ~80% token reduction vs raw source.
        """
        ...

    def token_estimate(self) -> int:
        """Rough token count of compact repr for LLM context budgeting."""
        return len(self.to_compact_repr()) // 4
```

- [ ] Implement full `ModuleStub` extraction using `ast.parse`
- [ ] Implement `to_compact_repr()` — output looks like interface declarations, not implementations
- [ ] Implement `ContextManager` in `copilot/context.py` that: takes a list of files, stubs each, orders by relevance score (files that import the target file = high relevance), fits within `max_context_tokens` budget
- [ ] Add `nikame stub <file>` CLI command — prints the compact repr so users can see exactly what goes to the LLM
- [ ] Add `nikame stub <file> --tokens` to show estimated token usage

### 1.7 Import Linter Enforcement

- [ ] Add `import-linter` as a dev dependency
- [ ] Create `.importlinter` config enforcing the layer contract:

```ini
[importlinter]
root_packages = nikame

[importlinter:contract:layers]
name = Layered architecture
type = layers
layers =
    nikame.cli
    nikame.tui
    nikame.copilot
    nikame.engines
    nikame.core
```

- [ ] Add `lint-imports` to CI and `make check`

---

## PHASE 2 — CLI Experience (fastcheat-grade)
**Timeline: Week 3**
**Goal: The CLI should feel as good as using `gh` or `cargo`. Every command is fast, beautiful, and does exactly what it says.**

### 2.1 Command Surface

```
nikame init [--config nikame.yaml] [--interactive]
nikame add <pattern-id> [--dry-run] [--no-confirm]
nikame remove <pattern-id> [--keep-files]
nikame list [--category auth|database|cache|...] [--installed]
nikame info <pattern-id>
nikame verify [--watch] [--json]
nikame diff [<pattern-id>]
nikame stub <file> [--tokens]
nikame validate [<config-file>]
nikame rollback [--to <snapshot-id>]
nikame snapshot list
nikame agent [--model <model>] [--provider <provider>]
nikame publish <pattern-dir>
nikame update [<pattern-id>]
nikame doctor                           # checks environment, dependencies, Ollama
```

### 2.2 `nikame init` — The Wizard

This is the first thing every user sees. It must be flawless.

**Interactive mode (default when no `--config` given):**

```
┌─────────────────────────────────────────────────────────┐
│  ⚡ NIKAME v2.0 — FastAPI Project Wizard                 │
└─────────────────────────────────────────────────────────┘

  Project name: █
  Description (optional):

  Select modules: (space to select, enter to confirm)
  ┌─ API ──────────────────────────────────────────────────┐
  │  [x] api.fastapi          FastAPI with async support   │
  │  [ ] api.graphql           Strawberry GraphQL          │
  └────────────────────────────────────────────────────────┘
  ┌─ Database ─────────────────────────────────────────────┐
  │  [x] database.postgres     PostgreSQL + SQLModel       │
  │  [ ] database.mysql        MySQL + SQLModel            │
  │  [ ] database.mongodb      Motor async MongoDB         │
  └────────────────────────────────────────────────────────┘
  ┌─ Cache ────────────────────────────────────────────────┐
  │  [x] cache.redis           Redis + redis-py async      │
  └────────────────────────────────────────────────────────┘
```

- [ ] Implement using Textual (not just Rich prompts — a real TUI app screen)
- [ ] Fuzzy search on module name inside the wizard
- [ ] Show pattern description and required env vars inline as user hovers each option
- [ ] Conflict detection runs live as user selects — incompatible options go red with explanation
- [ ] On confirm: writes `nikame.yaml`, shows summary, runs `nikame validate` automatically, prints next steps

**Non-interactive mode (`nikame init --config nikame.yaml`):**

- [ ] Load and validate config, show rich summary table, run conflict check, prompt for confirmation, proceed
- [ ] `--yes` flag to skip confirmation for CI usage

### 2.3 `nikame add` — The Flagship Command

This command is the core value proposition. It must be extraordinary.

```
$ nikame add auth.jwt

  ┌─ auth.jwt v2.1 ─────────────────────────────────────────────────────┐
  │  JWT Authentication with refresh token rotation                      │
  │                                                                      │
  │  Requires:   database.postgres ✓   cache.redis ✓                    │
  │  Conflicts:  auth.session (not installed) ✓                          │
  │                                                                      │
  │  Will create:                                                         │
  │    + app/api/auth/router.py                                          │
  │    + app/core/security.py                                            │
  │    + tests/api/test_auth.py                                          │
  │    + migrations/001_create_token_blacklist.sql                       │
  │                                                                      │
  │  Will modify:                                                         │
  │    ~ app/models/user.py  (add password_hash field)                   │
  │    ~ app/main.py         (register auth router)                       │
  │                                                                      │
  │  New env vars:                                                        │
  │    JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES        │
  └──────────────────────────────────────────────────────────────────────┘

  [d] View full diff   [y] Apply   [n] Cancel
```

- [ ] Pre-flight check: resolve requires, detect conflicts, abort with clear message if any fail
- [ ] Snapshot current state before any file operation
- [ ] Render diff preview using Rich's `Syntax` + custom diff renderer before asking confirmation
- [ ] `--dry-run` flag: print everything above but write nothing
- [ ] `--no-confirm` flag: skip the confirmation (for scripts)
- [ ] After injection: auto-run `nikame verify` and show result inline
- [ ] If verify fails: offer immediate rollback with `[r] Rollback`
- [ ] Update `.nikame/context.yaml` manifest on success
- [ ] Append new env vars to `.env.example` with generated safe example values

### 2.4 `nikame diff`

- [ ] `nikame diff auth.jwt` — show what `add` would do, without the confirmation flow
- [ ] Syntax-highlighted, side-by-side for modifications, clean create/delete markers
- [ ] `--json` output for programmatic use

### 2.5 `nikame doctor`

Runs before any command that needs the environment to be ready.

```
$ nikame doctor

  Environment Check
  ─────────────────────────────────────────
  Python version          3.11.9    ✓
  nikame version          2.0.0     ✓
  Ollama running          yes       ✓
  Ollama model found      qwen2.5-coder:7b  ✓
  Docker available        yes       ✓
  Project config valid    yes       ✓
  Manifest version        2         ✓
  ─────────────────────────────────────────
  All checks passed. Ready.
```

- [ ] Implement all checks above
- [ ] `--fix` flag: attempt to auto-fix issues (pull Ollama model, initialize manifest, etc.)
- [ ] `nikame doctor` runs implicitly before `nikame agent` and `nikame init`

### 2.6 `nikame rollback`

```
$ nikame rollback

  Snapshots
  ─────────────────────────────────────────
  1. 2024-04-12 14:32:01  Before: add auth.jwt
  2. 2024-04-12 13:15:44  Before: add cache.redis
  3. 2024-04-12 11:02:18  Before: init
  ─────────────────────────────────────────
  Select snapshot to restore: █
```

- [ ] Implement `SnapshotManager`: before each scaffold op, write snapshot to `.nikame/snapshots/{iso-timestamp}/`
- [ ] Snapshot contains: full copy of modified files, manifest state, `.env.example` state
- [ ] `nikame rollback` opens TUI picker, confirm → restore → re-run verify

### 2.7 `nikame list`

```
$ nikame list --category auth

  Authentication Patterns
  ─────────────────────────────────────────────────────────────────
  auth.jwt          JWT + refresh tokens          installed v2.1
  auth.session      Server-side session auth      available
  auth.oauth2       OAuth2 with multiple providers  available
  auth.magic-link   Passwordless email auth       available
  auth.api-key      API key authentication        available
  ─────────────────────────────────────────────────────────────────

  5 patterns  ·  1 installed  ·  nikame.dev/patterns for full registry
```

- [ ] Implement with Rich table output
- [ ] `--installed` flag to show only what's in the manifest
- [ ] `--json` for programmatic use

### 2.8 `nikame info`

```
$ nikame info auth.jwt

  auth.jwt  v2.1
  ─────────────────────────────────────────
  JWT Authentication with refresh token rotation and token blacklisting

  Category:    auth
  Tags:        security, stateless, api
  Requires:    database.postgres, cache.redis
  Conflicts:   auth.session
  Optional:    observability.sentry

  Files Created:
    app/api/auth/router.py
    app/core/security.py
    tests/api/test_auth.py

  Env Vars:
    JWT_SECRET_KEY              required
    JWT_ALGORITHM               default: HS256
    ACCESS_TOKEN_EXPIRE_MINUTES default: 30

  Docs: https://nikame.dev/patterns/auth/jwt
```

---

## PHASE 3 — The Agent TUI (opencode-grade)
**Timeline: Week 4–5**
**Goal: `nikame agent` is a first-class, full-screen terminal application. Not a chatbot loop. A genuine agentic IDE.**

### 3.1 Agent Architecture

The agent is not just an LLM wrapper. It's a structured loop:

```
Plan → Stub relevant files → Build context → Generate actions →
Preview actions → [User confirms] → Execute → Verify → Commit to manifest
       ↓ if verify fails
Diagnose → Rollback → Re-plan with failure context
```

```python
# nikame/copilot/agent.py

from dataclasses import dataclass
from enum import Enum

class ActionType(Enum):
    CREATE_FILE = "create_file"
    MODIFY_FILE = "modify_file"
    DELETE_FILE = "delete_file"
    RUN_MIGRATION = "run_migration"
    ADD_ENV_VAR = "add_env_var"
    ADD_DEPENDENCY = "add_dependency"

@dataclass
class AgentAction:
    type: ActionType
    target_path: str | None
    content: str | None
    reason: str             # LLM's explanation for this action
    confidence: float       # 0.0–1.0

@dataclass
class AgentPlan:
    goal: str
    context_files: list[str]   # files stubbed and included in context
    actions: list[AgentAction]
    estimated_risk: Literal["low", "medium", "high"]

@dataclass
class AgentResult:
    plan: AgentPlan
    actions_executed: list[AgentAction]
    verification: VerificationResult
    snapshot_id: str
    rolled_back: bool
```

- [ ] Implement `ActionPlanner`: given user goal + project stubs + manifest, produce `AgentPlan` via LLM
- [ ] LLM is prompted to respond in structured JSON (action list) — parse with Pydantic
- [ ] Implement `AgentLoop`: plan → show to user → execute approved actions → verify → commit or rollback
- [ ] Always create snapshot before executing any agent plan
- [ ] Token budget enforcement: if stubs exceed `max_context_tokens`, rank files by import proximity to the task and drop least relevant

### 3.2 Agent TUI Layout

Built with [Textual](https://textual.textualize.io). Full-screen. No scrolling chat window — this is a real application.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ⚡ NIKAME Agent  ·  my-api  ·  qwen2.5-coder:7b  ·  [q]quit  [?]help     │
├──────────────┬──────────────────────────────────────┬───────────────────────┤
│ PROJECT      │ DIFF / PREVIEW                       │ AGENT STREAM          │
│              │                                       │                       │
│ ▼ app/       │  app/api/auth/router.py  [new]        │ > Add JWT auth to     │
│   ▼ api/     │  ─────────────────────────────────── │   this project        │
│     auth/    │  + from fastapi import APIRouter      │                       │
│     users/   │  + from app.core.security import ...  │ Planning...           │
│   core/      │  +                                    │                       │
│   models/    │  + router = APIRouter(prefix="/auth") │ ✓ Stubbed 8 files     │
│ ▼ tests/     │  + @router.post("/login")             │ ✓ Built context       │
│   api/       │  + async def login(…):                │   (3,241 tokens)      │
│ nikame.yaml  │      …                                │                       │
│ .env.example │                                       │ Action Plan (4):      │
│              │  app/models/user.py  [modified]       │  + router.py          │
│              │  ─────────────────────────────────── │  + security.py        │
│              │    class User(SQLModel, table=True):  │  ~ user.py            │
│              │  +   password_hash: str | None        │  ~ main.py            │
│              │                                       │                       │
│              │                                       │ [y] Apply  [n] Cancel │
│              │                                       │ [e] Edit plan         │
├──────────────┴──────────────────────────────────────┴───────────────────────┤
│  STATUS  ·  Snapshot created  ·  Verify: ✓  ·  Ready                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Left panel — File Tree:**
- [ ] Live-updating Textual `Tree` widget
- [ ] Files affected by the current plan are highlighted in yellow
- [ ] Click a file to open it in the diff panel

**Center panel — Diff/Preview:**
- [ ] Syntax-highlighted diff using Rich `Syntax` inside a Textual `Static` widget
- [ ] Shows `[new]`, `[modified]`, `[deleted]` badges per file
- [ ] Tab between affected files

**Right panel — Agent Stream:**
- [ ] Streaming LLM output appears token-by-token using async generator
- [ ] Shows planning stages: "Stubbing files…", "Building context (3,241 tokens)…", "Generating plan…"
- [ ] Action plan appears as a checklist — each item shows status as it executes

**Bottom bar:**
- [ ] Always shows: snapshot status, last verify result, current model
- [ ] Keyboard shortcuts visible

### 3.3 Agent Keyboard Bindings

| Key | Action |
|-----|--------|
| `y` | Apply current plan |
| `n` | Cancel and clear |
| `e` | Edit the plan (opens inline editor) |
| `r` | Rollback to last snapshot |
| `v` | Run verify manually |
| `s` | Show stub for focused file |
| `d` | Toggle diff/source view |
| `tab` | Cycle between affected files |
| `?` | Help overlay |
| `q` | Quit (prompts if plan pending) |

### 3.4 LLM Provider Abstraction

```python
# nikame/copilot/providers/base.py

from typing import Protocol, AsyncIterator

class LLMProvider(Protocol):
    async def complete(
        self,
        messages: list[dict],
        system: str,
        stream: bool = False,
    ) -> str | AsyncIterator[str]: ...

    async def health_check(self) -> bool: ...

    @property
    def model_name(self) -> str: ...
```

- [ ] Implement `OllamaProvider` — streaming support via HTTPX async
- [ ] Implement `OpenAIProvider` — `openai` SDK, streaming
- [ ] Implement `AnthropicProvider` — `anthropic` SDK, streaming
- [ ] Implement `GroqProvider` — `groq` SDK, streaming
- [ ] Implement `ProviderFactory`: reads `copilot.provider` from config, returns correct provider
- [ ] API keys read from env vars only — never from config file
- [ ] `nikame doctor` verifies provider connectivity

---

## PHASE 4 — The Pattern Registry (shadcn-grade)
**Timeline: Week 6**
**Goal: A registry so good that people contribute to it.**

### 4.1 Pattern Categories

Build at minimum 3 solid patterns per category before launch. Quality over quantity.

| Category | Patterns |
|----------|----------|
| `api` | `api.fastapi`, `api.graphql`, `api.websocket`, `api.grpc` |
| `database` | `database.postgres`, `database.mysql`, `database.mongodb`, `database.sqlite` |
| `cache` | `cache.redis`, `cache.memcached` |
| `auth` | `auth.jwt`, `auth.session`, `auth.oauth2`, `auth.magic-link`, `auth.api-key` |
| `storage` | `storage.s3`, `storage.minio`, `storage.gcs` |
| `queue` | `queue.celery`, `queue.arq`, `queue.rq` |
| `observability` | `observability.prometheus`, `observability.sentry`, `observability.opentelemetry` |
| `infra` | `infra.docker`, `infra.docker-compose`, `infra.helm` |
| `testing` | `testing.pytest`, `testing.factories`, `testing.coverage` |
| `features` | `features.rate-limiting`, `features.pagination`, `features.search`, `features.webhooks`, `features.cron` |

Each pattern must have:
- [ ] `manifest.yaml` (required, validated on load)
- [ ] All templates in `templates/` directory (Jinja2, strict mode)
- [ ] Test template in `tests/` directory
- [ ] Entry in `nikame.dev` pattern browser docs

### 4.2 Pattern Template Quality Standards

All Jinja2 templates must:
- [ ] Pass `jinja2-lint` with zero warnings
- [ ] Be rendered with `autoescape=select_autoescape()` — no XSS in generated code
- [ ] Include `{# nikame:pattern auth.jwt v2.1 #}` header comment in generated files for traceability
- [ ] Generate code that passes `ruff check` and `mypy --strict` with zero errors
- [ ] Include type annotations on all generated functions
- [ ] Generate async functions for all route handlers (FastAPI best practice)

### 4.3 Patch Operations (AST-aware Merge)

For patterns that modify existing files (e.g., adding a field to a model), implement AST-aware patching rather than text replacement.

```python
# nikame/engines/patcher.py

import ast
import astor

class ASTMerger:
    """
    Merges generated code fragments into existing source files
    without destroying existing code.
    """

    def patch_class(
        self,
        source: str,
        class_name: str,
        new_fields: list[str],
        new_methods: list[str],
    ) -> str:
        """Add fields/methods to an existing class without touching other members."""
        ...

    def patch_imports(self, source: str, new_imports: list[str]) -> str:
        """Add imports, deduplicated, sorted via isort rules."""
        ...

    def patch_router_registration(
        self, source: str, router_import: str, router_include: str
    ) -> str:
        """Add router to main.py app.include_router() calls."""
        ...
```

- [ ] Implement `ASTMerger` using `ast` + `astor` (or `libcst` for lossless CST manipulation — prefer `libcst` for production quality)
- [ ] Add `patch` as a valid `operation` type in pattern manifests
- [ ] Fallback: if patch fails (can't find target), abort with helpful error rather than corrupting the file

### 4.4 `nikame publish`

Allow users to publish their own patterns.

```
$ nikame publish ./my-patterns/auth/webauthn

  Validating pattern manifest...          ✓
  Linting templates...                    ✓
  Running test render...                  ✓
  Checking for secrets in templates...    ✓
  
  Pattern: auth.webauthn v1.0
  Author:  omdeep-borkar
  
  Publish to nikame registry? [y/n]
```

- [ ] `nikame publish <dir>` validates the manifest, lints templates, does a test render to a temp dir, checks for accidental secrets in templates
- [ ] Publishes to `nikame-registry` GitHub repo via PR (API-based, opens browser to PR)
- [ ] Pattern marked as `community` until reviewed by maintainers

---

## PHASE 5 — Infrastructure Layer
**Timeline: Week 7**
**Goal: `nikame.yaml` → production-ready infrastructure, not just code.**

### 5.1 Docker Generation

```python
# nikame/infra/docker.py

class DockerfileGenerator:
    def generate(self, config: NikameConfig) -> str:
        """
        Multi-stage Dockerfile:
        - Stage 1: deps (uv/pip install)
        - Stage 2: runtime (non-root user, health check, signal handling)
        Respects resource_tier for memory limits.
        """

class ComposeGenerator:
    def generate(self, config: NikameConfig, manifest: ManifestV2) -> str:
        """
        docker-compose.yaml based on installed modules.
        Includes: service containers, networks, named volumes, health checks.
        Ports from manifest.ports_allocated — no collisions.
        """
```

- [ ] Multi-stage Dockerfile with `uv` for fast installs
- [ ] Non-root user in runtime stage
- [ ] Proper `SIGTERM` handler via `uvicorn` `--graceful-timeout`
- [ ] `docker-compose.yaml` with health checks for all services
- [ ] `.dockerignore` generation
- [ ] `nikame infra docker` regenerates infra files on demand

### 5.2 Kubernetes / Helm

- [ ] `nikame infra helm` generates a Helm chart skeleton
- [ ] `values.yaml` maps `resource_tier` to actual CPU/memory requests and limits
- [ ] Generates `HorizontalPodAutoscaler` for `large` tier

### 5.3 Cloud Provider Configs

- [ ] AWS: ECS task definition + ALB target group + RDS param group
- [ ] GCP: Cloud Run service YAML + Cloud SQL config
- [ ] Azure: Container App YAML
- [ ] All generated from `environment.target` in `nikame.yaml`

---

## PHASE 6 — Testing & Quality Infrastructure
**Timeline: Week 8**
**Goal: NIKAME must be the kind of project that other projects reference for testing standards.**

### 6.1 Test Structure

```
tests/
├── unit/
│   ├── core/
│   │   ├── test_config_schema.py       # NikameConfig validation, edge cases
│   │   ├── test_manifest.py            # manifest versioning + migration
│   │   ├── test_ast_stubber.py         # stub generation accuracy
│   │   ├── test_cycle_detector.py      # synthetic import graphs with known cycles
│   │   └── test_conflict_resolver.py   # pattern dependency resolution
│   ├── engines/
│   │   ├── test_scaffold_engine.py     # template rendering, file injection
│   │   ├── test_verify_engine.py       # verify output against known fixtures
│   │   └── test_rollback_engine.py     # snapshot + restore
│   └── copilot/
│       ├── test_context_manager.py     # token budgeting, file ranking
│       └── test_action_planner.py      # mock LLM responses → parsed actions
│
├── integration/
│   ├── test_init_flow.py              # full nikame init → verify
│   ├── test_add_flow.py               # full nikame add auth.jwt end-to-end
│   ├── test_rollback_flow.py          # add → break → rollback
│   └── test_conflict_flow.py          # conflicting pattern add → correct error
│
├── e2e/
│   ├── test_cli_init.py               # subprocess Typer CLI tests
│   ├── test_cli_add.py
│   └── test_cli_verify.py
│
└── fixtures/
    ├── configs/                        # sample nikame.yaml files
    ├── projects/                       # minimal FastAPI project trees for testing
    └── pattern_outputs/                # golden-file outputs for template rendering
```

### 6.2 Coverage and Quality Gates

- [ ] Minimum 90% line coverage enforced by CI — `pytest-cov` + `coverage` with `fail_under = 90`
- [ ] All public functions have docstrings — enforced by `pydocstyle`
- [ ] Golden file tests for all template renders — any change to a template must update the golden file explicitly
- [ ] Property-based tests for config validation using `hypothesis` — fuzz the config parser
- [ ] Mutation testing with `mutmut` — ensure tests actually catch logic errors

### 6.3 CI Pipeline

```yaml
# .github/workflows/ci.yml

jobs:
  quality:
    - ruff check .
    - ruff format --check .
    - mypy --strict nikame/
    - pyright nikame/
    - lint-imports
    - pydocstyle nikame/

  test:
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
        os: [ubuntu-latest, macos-latest, windows-latest]
    - pytest tests/unit tests/integration --cov=nikame --cov-fail-under=90

  e2e:
    - pytest tests/e2e --timeout=120

  security:
    - bandit -r nikame/ -ll           # security linting
    - pip-audit                        # dependency vulnerability scan
    - trufflehog filesystem .          # secret scanning

  changelog:
    - check CHANGELOG.md updated in PR
```

---

## PHASE 7 — Documentation Site
**Timeline: Week 9**
**Goal: Docs good enough that a senior engineer understands NIKAME in 10 minutes and wants to use it.**

### 7.1 Site Stack

- [ ] Use [Astro Starlight](https://starlight.astro.build) — fastest, cleanest CLI tool docs site
- [ ] Deploy to Cloudflare Pages at `nikame.dev`
- [ ] Auto-deploy on merge to `main`

### 7.2 Site Structure

```
nikame.dev/
├── /                    Getting started — 5-minute quickstart
├── /concepts/
│   ├── config           nikame.yaml spec with schema reference
│   ├── patterns         What patterns are and how they work
│   ├── manifest         The .nikame/ state directory explained
│   ├── ast-stubbing     Technical deep-dive on the AST stub system
│   └── agent            How the agent loop works
├── /patterns/           Full searchable pattern browser
│   ├── /auth/jwt
│   ├── /auth/session
│   └── ...
├── /cli/               Every command with examples
│   ├── /init
│   ├── /add
│   └── ...
├── /contributing/
│   ├── patterns         How to write and publish a pattern
│   └── core            Contributing to the core framework
└── /changelog
```

### 7.3 Content Requirements

- [ ] 5-minute quickstart that results in a running FastAPI project with JWT auth and Postgres — zero prior NIKAME knowledge required
- [ ] "How NIKAME Compares" page: vs. cookiecutter, vs. FastAPI generators, vs. Copilot — honest, accurate
- [ ] Pattern browser: searchable, filterable, shows manifest info, links to source in registry
- [ ] Interactive config builder: GUI → generate `nikame.yaml`
- [ ] Each pattern has its own docs page with: description, requirements, generated file tree, env vars, example usage

---

## PHASE 8 — The Launch Moment
**Timeline: Week 10**
**Goal: A launch that gets NIKAME on the front page of Hacker News.**

### 8.1 Demo Video

A 90-second screen recording that tells the complete story:

1. `nikame init` → TUI wizard → select FastAPI + Postgres + Redis → done
2. `nikame add auth.jwt` → diff preview → apply → verify passes
3. `nikame agent` → "Add rate limiting to the auth endpoint" → plan appears → apply → verify
4. `nikame rollback` → restore to before agent changes

Record at 1440p, narration optional but subtitles required.

### 8.2 PyPI v2.0.0

- [ ] Clean `v2.0.0` release — no legacy artifacts
- [ ] `pip install nikame` — works on macOS, Linux, Windows
- [ ] `uvx nikame` — works without even installing Python packages globally
- [ ] Auto-complete for `bash`, `zsh`, `fish` via Typer's built-in completion

### 8.3 Hacker News Post

Write the Show HN post before the launch. Title: **"Show HN: NIKAME — shadcn/ui for FastAPI backends, with a built-in agentic TUI"**

The post must include:
- What problem it solves (one paragraph)
- A link to the 90-second demo video
- A link to the quickstart
- A direct `pip install nikame` command that works without any other setup

### 8.4 Community

- [ ] GitHub Discussions enabled with categories: Q&A, Patterns (share yours), General
- [ ] Discord server linked from README and docs
- [ ] `GOVERNANCE.md` explaining how pattern PRs are reviewed and merged

---

## Architecture Non-Negotiables
**These are the laws of the codebase. No exceptions.**

1. **`core` has zero nikame-internal imports.** It's the kernel. It imports only stdlib and whitelist deps (pydantic, networkx, jinja2, libcst).

2. **`cli` has zero business logic.** Every command is ≤ 20 lines. Logic lives in engines.

3. **No subprocess for verification.** Ever. The `SyntaxVerifier` uses AST only.

4. **Every public function has a return type annotation.** `mypy --strict` must pass.

5. **Every scaffold operation creates a snapshot before touching the filesystem.** No exceptions.

6. **LLM is never called without explicit user confirmation of the plan.** The agent shows the plan first, always.

7. **`nikame.yaml` and `.nikame/context.yaml` are versioned.** Any schema change requires a migration function.

8. **Templates are never rendered without autoescape.** Use `select_autoescape()`.

9. **Secrets never go in config files.** Env vars only. `nikame doctor` warns if secrets are found in `nikame.yaml`.

10. **Every pattern in the registry has a `manifest.yaml`.** The registry loader refuses to load patterns without one.

---

## Dependency Budget
*Keep the install footprint small. Every dep is a security surface and a conflict risk.*

| Dep | Purpose | Optional? |
|-----|---------|-----------|
| `typer` | CLI framework | No |
| `rich` | Terminal output | No |
| `textual` | TUI framework | No |
| `pydantic[v2]` | Config + manifest validation | No |
| `jinja2` | Template rendering | No |
| `networkx` | Import graph + cycle detection | No |
| `libcst` | Lossless AST patching | No |
| `watchfiles` | `--watch` mode | No |
| `httpx[async]` | HTTP client for providers | No |
| `openai` | OpenAI provider | Optional: `cloud` |
| `anthropic` | Anthropic provider | Optional: `cloud` |
| `groq` | Groq provider | Optional: `cloud` |
| `docker` | Docker SDK | Optional: `infra` |

Install profiles:
```
pip install nikame               # core + ollama only
pip install nikame[cloud]        # + OpenAI, Anthropic, Groq
pip install nikame[infra]        # + Docker SDK
pip install nikame[all]          # everything
```

---

## Success Metrics (how to know it's 100/100)

| Metric | Target |
|--------|--------|
| `mypy --strict` errors | 0 |
| `ruff check` warnings | 0 |
| Test coverage | ≥ 90% |
| `nikame add auth.jwt` end-to-end time | < 4 seconds |
| `nikame verify` on 50-file project | < 500ms |
| PyPI install size | < 15MB |
| `nikame.dev` Lighthouse score | ≥ 95 |
| Pattern manifests with full test template | 100% |
| GitHub issues closed with "wontfix" in first 3 months | 0 |
| Time-to-working-project from `pip install` | < 5 minutes |

---

## Graveyard — What to Cut Forever

These features are in the current README or implied by the code. Cut them from v2.0. They add complexity without proportional value:

| Feature | Why to cut |
|---------|-----------|
| Kubernetes generation in core | Scope creep. Add as a plugin post-v2. |
| Cloud provider provisioning (AWS/GCP/Azure) in core | Same. Infra-as-code is a separate product. |
| "100+ patterns" claim | Deliver 30 exceptional patterns. Claim 30. |
| Subprocess smoke testing | Replaced entirely by static analysis. |
| `auto_wire.py` | Delete. It's a script, not a framework feature. |
| Multiple config file formats | One format: `nikame.yaml`. That's it. |

Cut these, ship the remaining things perfectly, and NIKAME is a 100/100 product.

---

*Last updated: April 2026 — NIKAME v2.0 Roadmap*
*Prepared for: Antogravity*
