"""Continuous Correctness Tests — Auto-Wiring Engine.

Tests that all 6 wiring passes correctly connect components.
"""
from __future__ import annotations

import copy

import pytest

from nikame.codegen.wiring.autowire import AutoWiringEngine


class TestRouterWiring:
    """Router wiring pass auto-registers routers in main.py."""

    def test_unwired_router_gets_wired(self):
        buf = {
            "services/api/app/main.py": '''from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def root():
    return {"ok": True}
''',
            "services/api/app/routers/users.py": '''from fastapi import APIRouter
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
async def list_users():
    return []
''',
        }
        engine = AutoWiringEngine()
        wired, report = engine.run(buf)
        main = wired["services/api/app/main.py"]
        assert "include_router" in main
        assert "users" in main.lower()
        assert report.total_actions > 0

    def test_already_wired_router_not_duplicated(self):
        buf = {
            "services/api/app/main.py": '''from fastapi import FastAPI
from services.api.app.routers.users import router as users_router
app = FastAPI()
app.include_router(users_router)
''',
            "services/api/app/routers/users.py": '''from fastapi import APIRouter
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
async def list_users():
    return []
''',
        }
        engine = AutoWiringEngine()
        wired, report = engine.run(buf)
        main = wired["services/api/app/main.py"]
        assert main.count("include_router") == 1


class TestLifespanWiring:
    """Lifespan wiring pass creates an asynccontextmanager lifespan."""

    def test_integrations_get_lifespan(self):
        buf = {
            "services/api/app/main.py": '''from fastapi import FastAPI
app = FastAPI()
''',
            "services/api/app/core/integrations/database.py": '''import os

async def startup():
    pass

async def shutdown():
    pass
''',
        }
        engine = AutoWiringEngine()
        wired, report = engine.run(buf)
        main = wired["services/api/app/main.py"]
        assert "lifespan" in main
        assert "asynccontextmanager" in main

    def test_dependency_ordering(self):
        buf = {
            "services/api/app/main.py": '''from fastapi import FastAPI
app = FastAPI()
''',
            "services/api/app/core/integrations/cache.py": '''import redis
async def startup():
    pass
''',
            "services/api/app/core/integrations/database.py": '''import sqlalchemy
async def startup():
    pass
''',
        }
        engine = AutoWiringEngine()
        wired, report = engine.run(buf)
        main = wired["services/api/app/main.py"]
        # Database should come before cache
        db_pos = main.find("database")
        cache_pos = main.find("cache")
        assert db_pos < cache_pos, "Database should start before cache"


class TestHealthCheckWiring:
    """Health check wiring pass aggregates health checks."""

    def test_health_checks_aggregated(self):
        buf = {
            "services/api/app/main.py": '''from fastapi import FastAPI
app = FastAPI()
''',
            "services/api/app/core/integrations/database.py": '''
async def health_check():
    return {"status": "ok"}
''',
            "services/api/app/core/integrations/cache.py": '''
async def health_check():
    return {"status": "ok"}
''',
        }
        engine = AutoWiringEngine()
        wired, report = engine.run(buf)
        # Should have a health endpoint file
        health_files = [k for k in wired if "health" in k and k.endswith(".py")]
        assert len(health_files) > 0
        health_content = wired[health_files[0]]
        assert "database" in health_content
        assert "cache" in health_content


class TestMiddlewareWiring:
    """Middleware wiring pass registers middleware in correct order."""

    def test_middleware_registered(self):
        buf = {
            "services/api/app/main.py": '''from fastapi import FastAPI
app = FastAPI()
''',
            "services/api/app/middleware/tracing.py": '''
class TracingMiddleware:
    def __init__(self, app):
        self.app = app
''',
            "services/api/app/middleware/rate_limit.py": '''
class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app
''',
        }
        engine = AutoWiringEngine()
        wired, report = engine.run(buf)
        main = wired["services/api/app/main.py"]
        assert "add_middleware(TracingMiddleware)" in main
        assert "add_middleware(RateLimitMiddleware)" in main

    def test_middleware_ordered_correctly(self):
        buf = {
            "services/api/app/main.py": '''from fastapi import FastAPI
app = FastAPI()
''',
            "services/api/app/middleware/rate_limit.py": '''
class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app
''',
            "services/api/app/middleware/tracing.py": '''
class TracingMiddleware:
    def __init__(self, app):
        self.app = app
''',
        }
        engine = AutoWiringEngine()
        wired, report = engine.run(buf)
        main = wired["services/api/app/main.py"]
        tracing_pos = main.find("TracingMiddleware")
        rate_pos = main.find("RateLimitMiddleware")
        assert tracing_pos < rate_pos, "Tracing should come before rate limiting"


class TestSettingsWiring:
    """Settings wiring pass generates a Settings class."""

    def test_settings_generated_from_env_refs(self):
        buf = {
            "services/api/app/main.py": '''import os
from fastapi import FastAPI
app = FastAPI(title=os.getenv("SERVICE_NAME"))
''',
            "services/api/app/config.py": '''import os
DB = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", "8000"))
''',
        }
        engine = AutoWiringEngine()
        wired, report = engine.run(buf)
        settings_files = [k for k in wired if "settings" in k]
        assert len(settings_files) > 0
        settings = wired[settings_files[0]]
        assert "database_url" in settings
        assert "port" in settings
        assert "service_name" in settings


class TestAutoWiringIntegration:
    """End-to-end test with all passes together."""

    def test_full_stack_buffer_wires_clean(self, full_stack_buffer):
        engine = AutoWiringEngine()
        wired, report = engine.run(full_stack_buffer)
        assert report.total_actions > 0
        assert "services/api/app/main.py" in wired
        main = wired["services/api/app/main.py"]
        # Should have routers, lifespan, middleware
        assert "include_router" in main
