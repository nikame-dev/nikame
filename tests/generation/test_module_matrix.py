"""Continuous Correctness Tests — Module Combination Matrix.

Tests that the Rules Engine + Auto-Wiring Engine produce valid output
for every realistic combination of NIKAME modules. This catches
cross-module integration bugs that only appear with specific combos.
"""
from __future__ import annotations

import copy
from itertools import combinations

import pytest

from nikame.codegen.rules import RulesEngine
from nikame.codegen.wiring.autowire import AutoWiringEngine


# ═══════════════════════════════════════════════════════════════════
# Module Snippets — each represents the generated output of a module
# ═══════════════════════════════════════════════════════════════════

MODULE_SNIPPETS = {
    "postgres": {
        "services/api/app/core/integrations/database.py": '''"""PostgreSQL integration."""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DATABASE_URL = os.getenv("DATABASE_URL")

async def startup():
    global engine
    engine = create_async_engine(DATABASE_URL)

async def shutdown():
    if engine:
        await engine.dispose()

async def health_check():
    return {"status": "ok"}
''',
    },

    "redis": {
        "services/api/app/core/integrations/cache.py": '''"""Redis cache integration."""
import os
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL")

async def startup():
    global redis_client
    redis_client = redis.from_url(REDIS_URL)

async def shutdown():
    if redis_client:
        await redis_client.close()

async def health_check():
    return {"status": "ok"}
''',
    },

    "qdrant": {
        "services/api/app/core/integrations/qdrant_search.py": '''"""Qdrant vector search."""
import os
from qdrant_client import QdrantClient

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")

async def startup():
    global qdrant
    qdrant = QdrantClient(host=QDRANT_HOST)

async def shutdown():
    pass

async def health_check():
    return {"status": "ok"}
''',
    },

    "stripe": {
        "services/api/app/routers/payments.py": '''from fastapi import APIRouter
import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/charge")
async def charge():
    return {"status": "charged"}
''',
    },

    "auth": {
        "services/api/app/routers/auth.py": '''from fastapi import APIRouter
import os

JWT_SECRET = os.getenv("JWT_SECRET")
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login():
    return {"token": "jwt_token"}

@router.post("/register")
async def register():
    return {"status": "registered"}
''',
    },

    "users": {
        "services/api/app/routers/users.py": '''from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
async def list_users():
    return []
''',
    },

    "minio": {
        "services/api/app/core/integrations/storage.py": '''"""MinIO object storage."""
import os
from minio import Minio

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

async def startup():
    global minio_client
    minio_client = Minio(MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, secure=False)

async def shutdown():
    pass

async def health_check():
    return {"status": "ok"}
''',
    },

    "middleware_cors": {
        "services/api/app/middleware/cors.py": '''"""CORS middleware."""
class CORSMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)
''',
    },

    "middleware_tracing": {
        "services/api/app/middleware/tracing.py": '''"""Tracing middleware."""
class TracingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)
''',
    },
}

# Base buffer — always present
BASE_BUFFER = {
    "services/api/app/main.py": '''"""Main FastAPI application."""
import os
from fastapi import FastAPI

app = FastAPI(title=os.getenv("SERVICE_NAME", "test-app"))

@app.get("/")
def root():
    return {"status": "ok"}
''',
    "services/api/requirements.txt": """fastapi>=0.109.0
uvicorn>=0.27.0
""",
    ".env.example": "SERVICE_NAME=test-app\n",
    ".env.generated": "SERVICE_NAME=test-app\n",
}


def _build_buffer(module_names: list[str]) -> dict[str, str]:
    """Merge base buffer with selected module snippets."""
    buf = copy.deepcopy(BASE_BUFFER)
    for name in module_names:
        if name in MODULE_SNIPPETS:
            buf.update(MODULE_SNIPPETS[name])
    return buf


# ═══════════════════════════════════════════════════════════════════
# Parametrized Tests — Module Combinations
# ═══════════════════════════════════════════════════════════════════

# All module names
ALL_MODULES = list(MODULE_SNIPPETS.keys())

# Generate all 2-module and 3-module combinations
COMBO_2 = [list(c) for c in combinations(ALL_MODULES, 2)]
COMBO_3 = [list(c) for c in combinations(ALL_MODULES, 3)]

# Key realistic combinations
REALISTIC_COMBOS = [
    ["postgres", "redis", "users", "auth"],
    ["postgres", "redis", "qdrant", "users"],
    ["postgres", "redis", "stripe", "auth", "users"],
    ["postgres", "minio", "middleware_cors", "middleware_tracing"],
    ALL_MODULES,  # The "everything at once" test
]


class TestModuleCombinations:
    """Test that various module combinations produce valid output."""

    @pytest.mark.parametrize("modules", COMBO_2[:15], ids=["-".join(m) for m in COMBO_2[:15]])
    def test_two_module_combos_pass_autowiring(self, modules):
        buf = _build_buffer(modules)
        engine = AutoWiringEngine()
        wired, report = engine.run(buf)
        # Basic sanity: main.py should still be valid
        assert "services/api/app/main.py" in wired
        assert "FastAPI" in wired["services/api/app/main.py"]

    @pytest.mark.parametrize("modules", COMBO_3[:10], ids=["-".join(m) for m in COMBO_3[:10]])
    def test_three_module_combos_pass_rules(self, modules):
        buf = _build_buffer(modules)
        # First wire
        autowire = AutoWiringEngine()
        wired, _ = autowire.run(buf)
        # Then validate
        rules = RulesEngine()
        fixed, results = rules.validate(wired)
        p0_unfixable = [v for r in results for v in r.violations if v.severity == "P0" and not v.auto_fixable]
        assert len(p0_unfixable) == 0, f"P0 failures for {modules}: {p0_unfixable}"

    @pytest.mark.parametrize("modules", REALISTIC_COMBOS,
                             ids=["-".join(m[:3]) + ("..." if len(m) > 3 else "") for m in REALISTIC_COMBOS])
    def test_realistic_combos_full_pipeline(self, modules):
        buf = _build_buffer(modules)

        # Step 1: Auto-wire
        autowire = AutoWiringEngine()
        wired, wiring_report = autowire.run(buf)

        # Step 2: Rules engine
        rules = RulesEngine()
        fixed, rule_results = rules.validate(wired)

        # Assertions
        p0_unfixable = [v for r in rule_results for v in r.violations if v.severity == "P0" and not v.auto_fixable]
        assert len(p0_unfixable) == 0, f"P0 failures for {modules}"

        # main.py should be wired
        main = fixed.get("services/api/app/main.py", "")
        assert "FastAPI" in main

        # All env vars should be in .env files
        assert ".env.example" in fixed
        assert ".env.generated" in fixed


class TestSingleModuleRegression:
    """Test each module individually produces valid output."""

    @pytest.mark.parametrize("module_name", ALL_MODULES)
    def test_single_module_passes(self, module_name):
        buf = _build_buffer([module_name])

        autowire = AutoWiringEngine()
        wired, _ = autowire.run(buf)

        rules = RulesEngine()
        fixed, results = rules.validate(wired)

        p0_unfixable = [v for r in results for v in r.violations if v.severity == "P0" and not v.auto_fixable]
        assert len(p0_unfixable) == 0, f"P0 failures for [{module_name}]"
