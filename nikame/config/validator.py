"""Cross-module validation and smart-default warnings.

Runs after Pydantic validation to catch semantic issues:
conflicting modules, missing dependencies, and suboptimal choices.
"""

from __future__ import annotations

from nikame.config.schema import NikameConfig
from nikame.exceptions import NikameModuleConflictError, NikameValidationError
from nikame.utils.logger import console, get_logger

_log = get_logger("config.validator")

# Smart-default recommendations: (user_choice, recommended, reason)
_SMART_DEFAULTS: list[tuple[str, str, str]] = [
    ("redis", "dragonfly", "Dragonfly is 25x more memory-efficient and Redis-compatible"),
    ("kafka", "redpanda", "RedPanda has no JVM, is 10x faster, and is Kafka-compatible"),
]


def validate_config(config: NikameConfig) -> list[str]:
    """Perform cross-module validation on a NikameConfig.

    Checks for:
    - Module conflicts (e.g., redis cache + dragonfly cache)
    - Missing dependencies
    - Smart-default recommendations (warnings, not errors)

    Args:
        config: Validated NikameConfig instance.

    Returns:
        List of warning messages (non-fatal).

    Raises:
        NikameValidationError: If hard conflicts or missing deps detected.
        NikameModuleConflictError: If conflicting modules are declared.
    """
    warnings: list[str] = []

    # Collect which modules are active
    active_modules: set[str] = set()

    if config.api:
        active_modules.add(f"api.{config.api.framework}")

    if config.databases:
        if config.databases.postgres:
            active_modules.add("database.postgres")
        if config.databases.redis:
            active_modules.add("database.redis")

    if config.messaging and config.messaging.redpanda:
        active_modules.add("messaging.redpanda")

    if config.cache:
        active_modules.add(f"cache.{config.cache.provider}")

    if config.storage:
        active_modules.add(f"storage.{config.storage.provider}")

    if config.auth:
        active_modules.add(f"auth.{config.auth.provider}")

    if config.gateway:
        active_modules.add(f"gateway.{config.gateway.provider}")

    if config.observability and config.observability.stack != "none":
        active_modules.add("observability.prometheus")
        active_modules.add("observability.grafana")

    _log.debug("Active modules: %s", active_modules)

    # ── Conflict checks ──

    if "database.redis" in active_modules and "cache.redis" in active_modules:
        raise NikameModuleConflictError(
            "Redis is declared as both database and cache. "
            "Use cache.dragonfly (recommended) or a single Redis instance."
        )

    # ── Dependency checks ──

    if config.api and config.api.auth.enabled and config.auth is None:
        raise NikameValidationError(
            "API auth is enabled but no auth provider is configured. "
            "Add an 'auth:' section to your nikame.yaml."
        )

    if config.api and config.api.rate_limiting.enabled:
        needs_cache = True
        if config.cache is None and (
            config.databases is None or config.databases.redis is None
        ):
            if needs_cache:
                raise NikameValidationError(
                    "API rate limiting requires a cache (dragonfly/redis). "
                    "Add 'cache:' or 'databases.redis:' to your config."
                )

    # ── Smart-default warnings ──

    if "database.redis" in active_modules:
        warnings.append(
            "💡 Consider using Dragonfly instead of Redis — "
            "25x more memory-efficient, fully Redis-compatible. "
            "Set cache.provider: dragonfly"
        )

    if config.databases and config.databases.postgres:
        if not config.databases.postgres.pgbouncer:
            warnings.append(
                "💡 pgBouncer is disabled for PostgreSQL. "
                "It's strongly recommended for production workloads."
            )

    # Print warnings
    for warning in warnings:
        console.print(f"  [warning]{warning}[/warning]")

    return warnings
