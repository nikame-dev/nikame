"""Production Code Standards — enforcement rules for NIKAME codegen.

These rules ensure every generated file meets production-grade standards:
- Async SQLAlchemy (no sync queries)
- Retry logic with tenacity on external calls
- Explicit response models / status codes on endpoints
- Structured logging with structlog
- Pool sizing from OptimizationProfile
- Cache error handling (miss/error/invalidation)
- Kafka DLQ handling
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from nikame.codegen.rules import BaseRule, RuleResult, RuleViolation
from nikame.utils.logger import get_logger

_log = get_logger("standards")


# ═══════════════════════════════════════════════════════════════════
# Rule: Async SQLAlchemy Enforcement
# ═══════════════════════════════════════════════════════════════════

class AsyncSQLAlchemyRule(BaseRule):
    """All database queries must use async sessions. No synchronous SQLAlchemy."""

    NAME = "async_sqlalchemy"
    DESCRIPTION = "Enforce async SQLAlchemy — no synchronous queries"

    # Sync patterns that should NOT appear
    _SYNC_PATTERNS = [
        (re.compile(r'\bfrom sqlalchemy\.orm\s+import\s+Session\b'), "Synchronous Session import"),
        (re.compile(r'\bfrom sqlalchemy\s+import\s+create_engine\b'), "Synchronous create_engine"),
        (re.compile(r'\bcreate_engine\s*\('), "Synchronous create_engine() call"),
        (re.compile(r'\bSession\s*\(\s*bind\s*='), "Synchronous Session(bind=)"),
        (re.compile(r'\bsessionmaker\s*\(\s*bind\s*='), "Synchronous sessionmaker(bind=)"),
        (re.compile(r'\.execute\s*\([^)]*\)\s*$', re.MULTILINE), "Possibly synchronous .execute()"),
    ]

    # Async patterns that SHOULD appear instead
    _ASYNC_REQUIRED = [
        "async_sessionmaker",
        "AsyncSession",
        "create_async_engine",
    ]

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        for path, content in file_buffer.items():
            if not path.endswith(".py"):
                continue
            if "sqlalchemy" not in content.lower():
                continue

            for pattern, desc in self._SYNC_PATTERNS:
                if pattern.search(content):
                    # Exception: alembic env.py is allowed to use sync engine
                    if "alembic" in path or "env.py" in Path(path).name:
                        continue
                    violations.append(RuleViolation(
                        rule=self.NAME,
                        severity="P0",
                        file=path,
                        message=f"{desc} — use async equivalent instead",
                        auto_fixable=True,
                    ))

        return RuleResult(rule_name=self.NAME, passed=len(violations) == 0, violations=violations)

    def fix(self, file_buffer: dict[str, str], violations: list[RuleViolation]) -> dict[str, str]:
        for v in violations:
            if not v.auto_fixable or v.rule != self.NAME:
                continue
            path = v.file
            if path not in file_buffer:
                continue
            content = file_buffer[path]

            # Replace sync with async equivalents
            content = content.replace(
                "from sqlalchemy.orm import Session",
                "from sqlalchemy.ext.asyncio import AsyncSession"
            )
            content = content.replace(
                "from sqlalchemy import create_engine",
                "from sqlalchemy.ext.asyncio import create_async_engine"
            )
            content = re.sub(
                r'\bcreate_engine\s*\(',
                'create_async_engine(',
                content
            )
            content = content.replace(
                "sessionmaker(bind=",
                "async_sessionmaker(bind="
            )
            file_buffer[path] = content

        return file_buffer


# ═══════════════════════════════════════════════════════════════════
# Rule: Retry Logic Enforcement
# ═══════════════════════════════════════════════════════════════════

class RetryLogicRule(BaseRule):
    """All external service calls must have retry logic with tenacity."""

    NAME = "retry_logic"
    DESCRIPTION = "Enforce retry logic on external HTTP/service calls"

    _EXTERNAL_CALL_PATTERNS = [
        re.compile(r'httpx\.\w+Client\s*\('),
        re.compile(r'requests\.(get|post|put|delete|patch)\s*\('),
        re.compile(r'aiohttp\.ClientSession\s*\('),
    ]

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        for path, content in file_buffer.items():
            if not path.endswith(".py"):
                continue

            has_external_calls = any(p.search(content) for p in self._EXTERNAL_CALL_PATTERNS)
            if not has_external_calls:
                continue

            # Check if tenacity retry is present
            has_retry = "tenacity" in content or "@retry" in content or "retry(" in content
            if not has_retry:
                violations.append(RuleViolation(
                    rule=self.NAME,
                    severity="P1",
                    file=path,
                    message="External HTTP calls without tenacity retry logic",
                    auto_fixable=True,
                ))

        return RuleResult(rule_name=self.NAME, passed=len(violations) == 0, violations=violations)

    def fix(self, file_buffer: dict[str, str], violations: list[RuleViolation]) -> dict[str, str]:
        for v in violations:
            if not v.auto_fixable or v.rule != self.NAME:
                continue
            path = v.file
            if path not in file_buffer:
                continue
            content = file_buffer[path]

            # Add tenacity import and a retry decorator hint
            retry_import = (
                "import os\n"
                "from tenacity import retry, stop_after_attempt, wait_exponential, before_log\n"
                "import logging\n\n"
                "logger = logging.getLogger(__name__)\n"
                "MAX_RETRIES = int(os.getenv('MAX_RETRY_ATTEMPTS', '3'))\n"
            )

            if "from tenacity" not in content:
                # Add import at top, after existing imports
                lines = content.splitlines()
                last_import = 0
                for i, line in enumerate(lines):
                    if line.startswith("import ") or line.startswith("from "):
                        last_import = i
                lines.insert(last_import + 1, "")
                lines.insert(last_import + 2, retry_import.strip())
                content = "\n".join(lines)

            file_buffer[path] = content

        return file_buffer


# ═══════════════════════════════════════════════════════════════════
# Rule: Explicit Response Models
# ═══════════════════════════════════════════════════════════════════

class ResponseModelRule(BaseRule):
    """All FastAPI endpoints must have explicit response models and status codes."""

    NAME = "response_models"
    DESCRIPTION = "Enforce response_model and status_code on all endpoints"

    _ENDPOINT_PATTERN = re.compile(
        r'@(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\'][^"\']+["\']\s*\)',
        re.MULTILINE,
    )

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        for path, content in file_buffer.items():
            if not path.endswith(".py"):
                continue

            for m in self._ENDPOINT_PATTERN.finditer(content):
                decorator_text = m.group(0)
                # Check for response_model or status_code
                if "response_model" not in decorator_text and "status_code" not in decorator_text:
                    # Get the function name from the next line
                    pos = m.end()
                    rest = content[pos:pos + 200]
                    fn_match = re.search(r'(?:async )?def (\w+)', rest)
                    fn_name = fn_match.group(1) if fn_match else "unknown"

                    # Skip health and root endpoints
                    if fn_name in ("root", "health", "health_check", "readiness", "liveness"):
                        continue

                    violations.append(RuleViolation(
                        rule=self.NAME,
                        severity="P1",
                        file=path,
                        message=f"Endpoint '{fn_name}' missing response_model/status_code",
                        auto_fixable=False,
                    ))

        return RuleResult(rule_name=self.NAME, passed=len(violations) == 0, violations=violations)


# ═══════════════════════════════════════════════════════════════════
# Rule: Structured Logging
# ═══════════════════════════════════════════════════════════════════

class StructuredLoggingRule(BaseRule):
    """All logging must use structlog, not stdlib logging."""

    NAME = "structured_logging"
    DESCRIPTION = "Enforce structlog for structured logging"

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        for path, content in file_buffer.items():
            if not path.endswith(".py"):
                continue

            # Check for stdlib logging usage (not just import)
            uses_stdlib = bool(re.search(r'logging\.(info|warning|error|debug|critical)\s*\(', content))
            uses_print_log = bool(re.search(r'\bprint\s*\(\s*f?["\'].*(?:error|warn|info|debug)', content, re.IGNORECASE))

            if uses_stdlib or uses_print_log:
                # Skip if structlog is already imported
                if "structlog" in content:
                    continue
                # Skip test files and config files
                if "test" in path or "conftest" in path or "alembic" in path:
                    continue

                violations.append(RuleViolation(
                    rule=self.NAME,
                    severity="P1",
                    file=path,
                    message="Uses stdlib logging — should use structlog for structured logging",
                    auto_fixable=True,
                ))

        return RuleResult(rule_name=self.NAME, passed=len(violations) == 0, violations=violations)

    def fix(self, file_buffer: dict[str, str], violations: list[RuleViolation]) -> dict[str, str]:
        for v in violations:
            if not v.auto_fixable or v.rule != self.NAME:
                continue
            path = v.file
            if path not in file_buffer:
                continue
            content = file_buffer[path]

            # Add structlog import
            if "import structlog" not in content:
                lines = content.splitlines()
                last_import = 0
                for i, line in enumerate(lines):
                    if line.startswith("import ") or line.startswith("from "):
                        last_import = i
                lines.insert(last_import + 1, "import structlog")
                lines.insert(last_import + 2, 'logger = structlog.get_logger(__name__)')
                content = "\n".join(lines)

            # Replace basic logging calls with structlog
            content = re.sub(r'logging\.(info|warning|error|debug|critical)\(',
                             r'logger.\1(', content)

            file_buffer[path] = content

        return file_buffer


# ═══════════════════════════════════════════════════════════════════
# Rule: Pool Sizing from Scale Tier
# ═══════════════════════════════════════════════════════════════════

class PoolSizingRule(BaseRule):
    """DB connection pools must be sized via env var, not hardcoded."""

    NAME = "pool_sizing"
    DESCRIPTION = "Enforce configurable pool sizing — no hardcoded pool_size"

    _HARDCODED_POOL = re.compile(r'pool_size\s*=\s*(\d+)')

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        for path, content in file_buffer.items():
            if not path.endswith(".py"):
                continue

            for m in self._HARDCODED_POOL.finditer(content):
                violations.append(RuleViolation(
                    rule=self.NAME,
                    severity="P1",
                    file=path,
                    message=f"Hardcoded pool_size={m.group(1)} — should read from env/settings",
                    auto_fixable=True,
                ))

        return RuleResult(rule_name=self.NAME, passed=len(violations) == 0, violations=violations)

    def fix(self, file_buffer: dict[str, str], violations: list[RuleViolation]) -> dict[str, str]:
        for v in violations:
            if not v.auto_fixable or v.rule != self.NAME:
                continue
            path = v.file
            if path not in file_buffer:
                continue
            content = file_buffer[path]

            # Replace hardcoded pool_size with env var
            content = self._HARDCODED_POOL.sub(
                'pool_size=int(os.getenv("DB_POOL_SIZE", "25"))',
                content,
            )
            # Ensure os is imported
            if "import os" not in content:
                content = "import os\n" + content

            file_buffer[path] = content

        return file_buffer


# ═══════════════════════════════════════════════════════════════════
# Rule: Cache Error Handling
# ═══════════════════════════════════════════════════════════════════

class CacheErrorHandlingRule(BaseRule):
    """Cache operations must handle miss, error, and invalidation separately."""

    NAME = "cache_error_handling"
    DESCRIPTION = "Enforce graceful cache error handling — never propagate cache errors"

    _BARE_CACHE_PATTERNS = [
        re.compile(r'await\s+redis_?\w*\.(get|set|delete)\s*\('),
        re.compile(r'cache\.(get|set|delete)\s*\('),
    ]

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        for path, content in file_buffer.items():
            if not path.endswith(".py"):
                continue

            has_cache_call = any(p.search(content) for p in self._BARE_CACHE_PATTERNS)
            if not has_cache_call:
                continue

            # Check if there's try/except around cache calls
            has_error_handling = "except" in content and ("redis" in content.lower() or "cache" in content.lower())
            if not has_error_handling:
                violations.append(RuleViolation(
                    rule=self.NAME,
                    severity="P1",
                    file=path,
                    message="Cache operations without try/except — cache errors should not propagate",
                    auto_fixable=False,
                ))

        return RuleResult(rule_name=self.NAME, passed=len(violations) == 0, violations=violations)


# ═══════════════════════════════════════════════════════════════════
# Rule: Kafka DLQ Handling
# ═══════════════════════════════════════════════════════════════════

class KafkaDLQRule(BaseRule):
    """Kafka consumers must have dead letter queue handling."""

    NAME = "kafka_dlq"
    DESCRIPTION = "Enforce DLQ handling for Kafka consumers"

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        for path, content in file_buffer.items():
            if not path.endswith(".py"):
                continue

            # Check for consumer patterns
            has_consumer = (
                "Consumer(" in content
                or "consume(" in content
                or "subscribe(" in content
            ) and ("kafka" in content.lower() or "confluent" in content.lower())

            if not has_consumer:
                continue

            # Check for DLQ pattern
            has_dlq = "dlq" in content.lower() or "dead_letter" in content.lower() or "dead letter" in content.lower()
            if not has_dlq:
                violations.append(RuleViolation(
                    rule=self.NAME,
                    severity="P1",
                    file=path,
                    message="Kafka consumer without DLQ handling — failed messages should go to a DLQ topic",
                    auto_fixable=False,
                ))

        return RuleResult(rule_name=self.NAME, passed=len(violations) == 0, violations=violations)


# ═══════════════════════════════════════════════════════════════════
# Registry: all production standards
# ═══════════════════════════════════════════════════════════════════

PRODUCTION_RULES: list[BaseRule] = [
    AsyncSQLAlchemyRule(),
    RetryLogicRule(),
    ResponseModelRule(),
    StructuredLoggingRule(),
    PoolSizingRule(),
    CacheErrorHandlingRule(),
    KafkaDLQRule(),
]
