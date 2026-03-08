"""Continuous Correctness Tests — Rules Engine.

Tests that every rule correctly detects violations and auto-fixes them.
These tests run in CI to prevent regressions in code generation quality.
"""
from __future__ import annotations

import copy

import pytest

from nikame.codegen.rules import RulesEngine, RuleViolation


class TestImportCheck:
    """Import check rule catches syntax errors."""

    def test_valid_python_passes(self, minimal_buffer):
        engine = RulesEngine()
        _, results = engine.validate(minimal_buffer)
        import_result = next(r for r in results if r.rule_name == "import_check")
        assert import_result.passed

    def test_syntax_error_fails(self, minimal_buffer):
        buf = copy.deepcopy(minimal_buffer)
        buf["services/api/app/broken.py"] = "def foo(\n  # missing closing paren"
        engine = RulesEngine()
        _, results = engine.validate(buf)
        import_result = next(r for r in results if r.rule_name == "import_check")
        assert not import_result.passed


class TestRequirementsCheck:
    """Requirements check rule catches missing packages."""

    def test_missing_package_detected(self, minimal_buffer):
        buf = copy.deepcopy(minimal_buffer)
        buf["services/api/app/notifier.py"] = "import httpx\n"
        engine = RulesEngine()
        _, results = engine.validate(buf)
        req_result = next(r for r in results if r.rule_name == "requirements_check")
        # Should have been auto-fixed
        assert "httpx" in buf.get("services/api/requirements.txt", "")

    def test_stdlib_not_flagged(self, minimal_buffer):
        buf = copy.deepcopy(minimal_buffer)
        buf["services/api/app/utils.py"] = "import os\nimport sys\nimport json\n"
        engine = RulesEngine()
        _, results = engine.validate(buf)
        req_result = next(r for r in results if r.rule_name == "requirements_check")
        assert req_result.passed

    def test_internal_packages_not_flagged(self, minimal_buffer):
        buf = copy.deepcopy(minimal_buffer)
        buf["services/api/app/foo.py"] = "from services.api.app import main\n"
        engine = RulesEngine()
        _, results = engine.validate(buf)
        req_result = next(r for r in results if r.rule_name == "requirements_check")
        assert req_result.passed


class TestEnvCheck:
    """Env check rule catches missing env var declarations."""

    def test_missing_env_var_detected_and_fixed(self, minimal_buffer):
        buf = copy.deepcopy(minimal_buffer)
        buf["services/api/app/config.py"] = 'DB = os.getenv("DATABASE_URL")\n'
        engine = RulesEngine()
        fixed, results = engine.validate(buf)
        assert "DATABASE_URL" in fixed.get(".env.example", "")
        assert "DATABASE_URL" in fixed.get(".env.generated", "")

    def test_declared_env_var_passes(self, minimal_buffer):
        buf = copy.deepcopy(minimal_buffer)
        buf[".env.example"] = "SERVICE_NAME=test\nFOO=bar\n"
        buf[".env.generated"] = "SERVICE_NAME=test\nFOO=bar\n"
        buf["services/api/app/svc.py"] = 'x = os.getenv("FOO")\n'
        engine = RulesEngine()
        _, results = engine.validate(buf)
        env_result = next(r for r in results if r.rule_name == "env_check")
        assert env_result.passed


class TestDockerfileCheck:
    """Dockerfile check rule catches missing Dockerfiles for build services."""

    def test_missing_dockerfile_auto_generated(self):
        buf = {
            "infra/docker-compose.yml": """services:
  api:
    build:
      context: ../services/api
      dockerfile: Dockerfile
""",
        }
        engine = RulesEngine()
        fixed, results = engine.validate(buf)
        assert "services/api/Dockerfile" in fixed

    def test_existing_dockerfile_passes(self):
        buf = {
            "infra/docker-compose.yml": """services:
  api:
    build:
      context: ../services/api
""",
            "services/api/Dockerfile": "FROM python:3.11\n",
        }
        engine = RulesEngine()
        _, results = engine.validate(buf)
        df_result = next(r for r in results if r.rule_name == "dockerfile_check")
        assert df_result.passed


class TestSecretScan:
    """Secret scan rule catches hardcoded secrets."""

    def test_hardcoded_aws_key_fails(self, minimal_buffer):
        buf = copy.deepcopy(minimal_buffer)
        buf["services/api/app/bad.py"] = 'key = "AKIAIOSFODNN7VAR1234"\n'
        engine = RulesEngine()
        _, results = engine.validate(buf)
        secret_result = next(r for r in results if r.rule_name == "secret_scan")
        assert not secret_result.passed

    def test_env_var_secret_passes(self, minimal_buffer):
        buf = copy.deepcopy(minimal_buffer)
        buf["services/api/app/good.py"] = 'key = os.getenv("AWS_ACCESS_KEY")\n'
        engine = RulesEngine()
        _, results = engine.validate(buf)
        secret_result = next(r for r in results if r.rule_name == "secret_scan")
        assert secret_result.passed


class TestRouterCheck:
    """Router check rule catches unregistered routers."""

    def test_unwired_router_gets_fixed(self):
        buf = {
            "services/api/app/main.py": '''from fastapi import FastAPI
app = FastAPI()

# NIKAME ROUTERS

@app.get("/")
def root():
    return {"ok": True}
''',
            "services/api/app/routers/users.py": '''from fastapi import APIRouter
router = APIRouter(prefix="/users")

@router.get("/")
async def list_users():
    return []
''',
        }
        engine = RulesEngine()
        fixed, results = engine.validate(buf)
        main_content = fixed["services/api/app/main.py"]
        assert "include_router" in main_content


class TestRulesEngineIntegration:
    """End-to-end test: all rules run together without crashing."""

    def test_minimal_buffer_passes_clean(self, minimal_buffer):
        engine = RulesEngine()
        _, results = engine.validate(minimal_buffer)
        p0_failures = [v for r in results for v in r.violations if v.severity == "P0" and not v.auto_fixable]
        assert len(p0_failures) == 0

    def test_full_stack_buffer_passes_after_fixes(self, full_stack_buffer):
        engine = RulesEngine()
        fixed, results = engine.validate(full_stack_buffer)
        p0_failures = [v for r in results for v in r.violations if v.severity == "P0" and not v.auto_fixable]
        assert len(p0_failures) == 0


class TestProductionStandards:
    """Tests for Phase 3 Production Code Standards."""

    def test_async_sqlalchemy_enforced(self):
        buf = {
            "app/db.py": "from sqlalchemy.orm import Session\nengine = create_engine('sqlite:///')"
        }
        engine = RulesEngine()
        fixed, results = engine.validate(buf)
        content = fixed["app/db.py"]
        assert "AsyncSession" in content
        assert "create_async_engine" in content

    def test_retry_logic_hint_added(self):
        buf = {
            "app/client.py": "import httpx\nasync def call(): httpx.get('url')"
        }
        engine = RulesEngine()
        fixed, results = engine.validate(buf)
        content = fixed["app/client.py"]
        assert "tenacity" in content
        assert "retry" in content

    def test_response_model_warning(self):
        buf = {
            "app/api.py": "@router.get('/data')\ndef get_data(): return {}"
        }
        engine = RulesEngine()
        _, results = engine.validate(buf)
        res = next(r for r in results if r.rule_name == "response_models")
        assert not res.passed

    def test_structured_logging_autofix(self):
        buf = {
            "app/log.py": "import logging\nlogging.info('test')"
        }
        engine = RulesEngine()
        fixed, results = engine.validate(buf)
        content = fixed["app/log.py"]
        assert "structlog" in content
        assert "logger.info" in content

    def test_pool_sizing_autofix(self):
        buf = {
            "app/db.py": "engine = create_async_engine(url, pool_size=10)"
        }
        engine = RulesEngine()
        fixed, results = engine.validate(buf)
        content = fixed["app/db.py"]
        assert 'os.getenv("DB_POOL_SIZE"' in content
