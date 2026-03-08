"""Auto-Wiring Engine for NIKAME.

Runs after all code generation is complete and before files are written to disk.
Reads the entire generated codebase as an in-memory tree and performs automatic
wiring passes to ensure all components are correctly connected.

Wiring Pass Order:
  1. Router wiring — register FastAPI routers in main.py
  2. Lifespan wiring — wire startup/shutdown for integration clients
  3. Health check wiring — aggregate health checks into /health endpoint
  4. Middleware wiring — register middleware classes in correct order
  5. Settings wiring — declare all env vars in a Settings class
  6. Import wiring — verify all cross-file imports resolve
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nikame.utils.logger import console, get_logger

_log = get_logger("autowire")


# ─────────────────────── Data Classes ────────────────────────────

@dataclass
class WiringAction:
    """A single auto-wiring action that was performed."""
    pass_name: str
    description: str
    file: str


@dataclass
class WiringReport:
    """Summary of all wiring actions performed."""
    actions: list[WiringAction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_actions(self) -> int:
        return len(self.actions)


# ─────────────────── Helper: Find main.py ────────────────────────

def _find_main_py(buffer: dict[str, str]) -> str | None:
    """Find the main FastAPI application file in the buffer."""
    candidates = [
        k for k in buffer
        if k.endswith("main.py") and ("app" in k or "services" in k)
    ]
    # Prefer the one with FastAPI() in it
    for c in candidates:
        if "FastAPI" in buffer.get(c, ""):
            return c
    return candidates[0] if candidates else None


# ═══════════════════════════════════════════════════════════════════
# PASS 1: Router Wiring
# ═══════════════════════════════════════════════════════════════════

_ROUTER_DEF = re.compile(r'(\w+)\s*=\s*APIRouter\(')
_ROUTER_PREFIX = re.compile(r'prefix\s*=\s*["\']([^"\']*)["\']')
_ROUTER_TAGS = re.compile(r'tags\s*=\s*\[([^\]]*)\]')
_INCLUDE_ROUTER = re.compile(r'app\.include_router\(([^)]+)\)')


def _router_wiring_pass(buffer: dict[str, str], report: WiringReport) -> dict[str, str]:
    """Find every FastAPI router and ensure it is registered in main.py."""
    main_py = _find_main_py(buffer)
    if not main_py:
        return buffer

    main_content = buffer[main_py]

    # Parse existing include_router calls
    existing_includes = set()
    for match in _INCLUDE_ROUTER.finditer(main_content):
        existing_includes.add(match.group(1).split(",")[0].strip())

    # Scan all files for router definitions
    routers_to_wire: list[dict[str, str]] = []

    for path, content in buffer.items():
        if path == main_py or not path.endswith(".py"):
            continue
        if "APIRouter" not in content:
            continue

        for m in _ROUTER_DEF.finditer(content):
            var_name = m.group(1)

            # Extract prefix and tags if available
            prefix_m = _ROUTER_PREFIX.search(content)
            prefix = prefix_m.group(1) if prefix_m else f"/{Path(path).stem}"
            tags_m = _ROUTER_TAGS.search(content)
            tags = tags_m.group(1).strip() if tags_m else f'"{Path(path).stem}"'

            # Build module import path
            module_path = path.replace("/", ".").replace(".py", "")

            # Check if this router is already included
            # Check for both direct var reference and module-qualified reference
            already_included = False
            for inc in existing_includes:
                if var_name in inc or Path(path).stem in inc:
                    already_included = True
                    break

            if not already_included:
                routers_to_wire.append({
                    "var": var_name,
                    "module": module_path,
                    "prefix": prefix,
                    "tags": tags,
                    "source": path,
                })

    if not routers_to_wire:
        return buffer

    # Wire the routers into main.py
    lines = main_content.splitlines()

    # Find the last import line
    last_import_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_idx = i

    # Find the router registration section
    router_marker = None
    for i, line in enumerate(lines):
        if "# NIKAME ROUTERS" in line or "include_router" in line:
            router_marker = i
            break

    # Add imports and registrations
    import_additions = []
    register_additions = []

    for r in routers_to_wire:
        # Create unique alias to avoid collisions
        alias = f"{Path(r['source']).stem}_{r['var']}"
        import_line = f"from {r['module']} import {r['var']} as {alias}"
        register_line = f"app.include_router({alias}, prefix=\"{r['prefix']}\", tags=[{r['tags']}])"

        if import_line not in main_content:
            import_additions.append(import_line)
        if alias not in main_content:
            register_additions.append(register_line)

        report.actions.append(WiringAction(
            pass_name="router_wiring",
            description=f"Registered router '{r['var']}' from {r['source']} at prefix={r['prefix']}",
            file=main_py,
        ))

    # Insert imports
    for imp in reversed(import_additions):
        lines.insert(last_import_idx + 1, imp)

    # Insert registrations after the marker or at end
    if router_marker is not None:
        insert_at = router_marker + 1 + len(import_additions)
        for reg in reversed(register_additions):
            lines.insert(insert_at, reg)
    else:
        # Find @app.get("/") and insert before it
        for i, line in enumerate(lines):
            if '@app.get("/")' in line or "@app.get('/')" in line:
                for reg in reversed(register_additions):
                    lines.insert(i, reg)
                lines.insert(i, "")
                break
        else:
            # Append at end
            lines.append("")
            lines.extend(register_additions)

    buffer[main_py] = "\n".join(lines)
    return buffer


# ═══════════════════════════════════════════════════════════════════
# PASS 2: Lifespan Wiring
# ═══════════════════════════════════════════════════════════════════

# Startup dependency ordering — earlier categories start first
_LIFESPAN_ORDER = [
    "database",    # db, postgres, sqlalchemy
    "cache",       # redis, dragonfly, memcached
    "messaging",   # kafka, redpanda, rabbitmq
    "search",      # qdrant, elasticsearch, meilisearch
    "storage",     # minio, s3
    "ml",          # mlflow, triton, ollama
    "application", # everything else
]

_CATEGORY_KEYWORDS = {
    "database": ["database", "db", "postgres", "sqlalchemy", "alembic", "session"],
    "cache": ["cache", "redis", "dragonfly", "memcached"],
    "messaging": ["kafka", "redpanda", "rabbitmq", "pubsub", "message", "event"],
    "search": ["qdrant", "elasticsearch", "meilisearch", "vector", "search"],
    "storage": ["minio", "s3", "storage", "bucket", "object_store"],
    "ml": ["mlflow", "triton", "ollama", "model", "inference", "embedding"],
}


def _categorize_integration(path: str, content: str) -> str:
    """Determine the category of an integration for startup ordering."""
    path_lower = path.lower()
    content_lower = content.lower()

    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in path_lower or kw in content_lower for kw in keywords):
            return category
    return "application"


def _lifespan_wiring_pass(buffer: dict[str, str], report: WiringReport) -> dict[str, str]:
    """Wire startup/shutdown for all integration clients into the lifespan."""
    main_py = _find_main_py(buffer)
    if not main_py:
        return buffer

    main_content = buffer[main_py]

    # Find integration files with startup/shutdown functions
    integrations: list[dict[str, Any]] = []

    for path, content in buffer.items():
        if not path.endswith(".py") or path == main_py:
            continue

        has_startup = bool(re.search(r'async def (?:startup|connect|init)\b', content))
        has_shutdown = bool(re.search(r'async def (?:shutdown|disconnect|close)\b', content))

        if not has_startup and not has_shutdown:
            continue

        module_name = Path(path).stem
        module_path = path.replace("/", ".").replace(".py", "")
        category = _categorize_integration(path, content)

        # Extract function names
        startup_fn = None
        shutdown_fn = None
        for fn_name in ["startup", "connect", "init"]:
            if f"async def {fn_name}" in content:
                startup_fn = fn_name
                break
        for fn_name in ["shutdown", "disconnect", "close"]:
            if f"async def {fn_name}" in content:
                shutdown_fn = fn_name
                break

        integrations.append({
            "name": module_name,
            "module": module_path,
            "category": category,
            "startup_fn": startup_fn,
            "shutdown_fn": shutdown_fn,
            "path": path,
        })

    if not integrations:
        return buffer

    # Sort by lifespan order
    order_map = {cat: i for i, cat in enumerate(_LIFESPAN_ORDER)}
    integrations.sort(key=lambda x: order_map.get(x["category"], len(_LIFESPAN_ORDER)))

    # Check if main.py already has a lifespan
    has_lifespan = "async def lifespan" in main_content or "@asynccontextmanager" in main_content

    if not has_lifespan:
        # Generate a lifespan context manager
        startup_lines = []
        shutdown_lines = []
        import_lines = []

        for intg in integrations:
            alias = f"{intg['name']}_client"
            import_lines.append(f"from {intg['module']} import {intg['startup_fn'] or 'startup'} as {alias}_startup")
            if intg["startup_fn"]:
                startup_lines.append(f"    await {alias}_startup()  # {intg['category']}")
            if intg["shutdown_fn"]:
                import_lines.append(f"from {intg['module']} import {intg['shutdown_fn']} as {alias}_shutdown")
                shutdown_lines.append(f"        await {alias}_shutdown()")

            report.actions.append(WiringAction(
                pass_name="lifespan_wiring",
                description=f"Wired {intg['name']} ({intg['category']}) into lifespan",
                file=main_py,
            ))

        lifespan_block = """
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    # Startup (ordered: database → cache → messaging → search → storage → ml → app)
{startup}
    yield
    # Shutdown (reverse order)
    try:
{shutdown}
    except Exception:
        pass
""".format(
            startup="\n".join(startup_lines) if startup_lines else "    pass",
            shutdown="\n".join(shutdown_lines) if shutdown_lines else "        pass",
        )

        # Insert imports and lifespan into main.py
        lines = main_content.splitlines()

        # Add imports at the top
        last_import = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                last_import = i
        for imp in reversed(import_lines):
            if imp not in main_content:
                lines.insert(last_import + 1, imp)

        # Add lifespan block before FastAPI() instantiation
        for i, line in enumerate(lines):
            if "FastAPI(" in line:
                # Insert lifespan block before FastAPI
                for bl in reversed(lifespan_block.strip().splitlines()):
                    lines.insert(i, bl)
                # Update FastAPI() call to include lifespan
                lines[i + len(lifespan_block.strip().splitlines())] = line.replace(
                    "FastAPI(",
                    "FastAPI(lifespan=lifespan, "
                )
                break

        buffer[main_py] = "\n".join(lines)

    return buffer


# ═══════════════════════════════════════════════════════════════════
# PASS 3: Health Check Wiring
# ═══════════════════════════════════════════════════════════════════

def _health_check_wiring_pass(buffer: dict[str, str], report: WiringReport) -> dict[str, str]:
    """Aggregate health checks from all services into a unified /health endpoint."""
    # Find all health check functions
    health_checks: list[dict[str, str]] = []

    for path, content in buffer.items():
        if not path.endswith(".py"):
            continue

        # Look for health check functions
        health_match = re.search(r'async def (health_check|check_health|health)\b', content)
        if health_match and "integrations" in path:
            fn_name = health_match.group(1)
            module_name = Path(path).stem
            module_path = path.replace("/", ".").replace(".py", "")

            health_checks.append({
                "name": module_name,
                "module": module_path,
                "fn": fn_name,
                "path": path,
            })

    if not health_checks:
        return buffer

    # Find or create a health endpoint file
    health_file = None
    for path in buffer:
        if "health" in path and path.endswith(".py") and "endpoint" in path:
            health_file = path
            break

    if not health_file:
        # Look for any health route file
        for path in buffer:
            if "health" in Path(path).stem and path.endswith(".py"):
                health_file = path
                break

    if not health_file:
        # Create one
        health_file = "services/api/app/api/v1/endpoints/health.py"

    # Build aggregated health check
    imports = []
    checks = []
    for hc in health_checks:
        alias = f"{hc['name']}_health"
        imports.append(f"from {hc['module']} import {hc['fn']} as {alias}")
        checks.append(f'        "{hc["name"]}": await {alias}(),')

        report.actions.append(WiringAction(
            pass_name="health_check_wiring",
            description=f"Added {hc['name']} health check to /health",
            file=health_file,
        ))

    health_content = '''"""Aggregated health check endpoint — auto-wired by NIKAME."""
from fastapi import APIRouter

{imports}

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Unified health check for all services."""
    checks = {{
{checks}
    }}

    all_healthy = all(
        isinstance(v, dict) and v.get("status") == "ok"
        if isinstance(v, dict) else v
        for v in checks.values()
    )

    return {{
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
    }}
'''.format(
        imports="\n".join(imports),
        checks="\n".join(checks),
    )

    buffer[health_file] = health_content
    return buffer


# ═══════════════════════════════════════════════════════════════════
# PASS 4: Middleware Wiring
# ═══════════════════════════════════════════════════════════════════

# Middleware ordering — earlier items are added first (outer → inner)
_MIDDLEWARE_ORDER = [
    "tracing",      # OpenTelemetry, request tracing
    "cors",         # CORS headers
    "auth",         # Authentication / JWT
    "rate_limit",   # Rate limiting
    "logging",      # Request/response logging
    "compression",  # Gzip compression
]

_MIDDLEWARE_KEYWORDS = {
    "tracing": ["tracing", "telemetry", "otel", "span", "trace"],
    "cors": ["cors", "cross_origin", "allow_origin"],
    "auth": ["auth", "jwt", "bearer", "token_verify"],
    "rate_limit": ["rate_limit", "throttle", "slowapi", "limiter"],
    "logging": ["logging", "access_log", "request_log"],
    "compression": ["compress", "gzip", "brotli"],
}


def _middleware_wiring_pass(buffer: dict[str, str], report: WiringReport) -> dict[str, str]:
    """Register middleware classes in the correct order."""
    main_py = _find_main_py(buffer)
    if not main_py:
        return buffer

    main_content = buffer[main_py]

    # Find middleware files
    middlewares: list[dict[str, Any]] = []

    for path, content in buffer.items():
        if not path.endswith(".py") or "middleware" not in path:
            continue

        # Look for middleware class or add_middleware patterns
        class_match = re.search(r'class\s+(\w+Middleware)\b', content)
        if class_match:
            cls_name = class_match.group(1)
            module_path = path.replace("/", ".").replace(".py", "")

            # Categorize
            category = "logging"  # default
            path_lower = path.lower()
            content_lower = content.lower()
            for cat, keywords in _MIDDLEWARE_KEYWORDS.items():
                if any(kw in path_lower or kw in content_lower for kw in keywords):
                    category = cat
                    break

            if cls_name not in main_content:
                middlewares.append({
                    "class": cls_name,
                    "module": module_path,
                    "category": category,
                    "path": path,
                })

    if not middlewares:
        return buffer

    # Sort by middleware priority
    order_map = {cat: i for i, cat in enumerate(_MIDDLEWARE_ORDER)}
    middlewares.sort(key=lambda x: order_map.get(x["category"], len(_MIDDLEWARE_ORDER)))

    # Inject into main.py
    lines = main_content.splitlines()
    last_import = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("import ") or line.strip().startswith("from "):
            last_import = i

    # Build additions
    import_lines = []
    middleware_lines = []

    for mw in middlewares:
        imp = f"from {mw['module']} import {mw['class']}"
        reg = f"app.add_middleware({mw['class']})"

        if imp not in main_content:
            import_lines.append(imp)
        if reg not in main_content:
            middleware_lines.append(reg)

        report.actions.append(WiringAction(
            pass_name="middleware_wiring",
            description=f"Registered {mw['class']} middleware ({mw['category']} priority)",
            file=main_py,
        ))

    # Insert imports
    for imp in reversed(import_lines):
        lines.insert(last_import + 1, imp)

    # Insert middleware after app = FastAPI(...)
    for i, line in enumerate(lines):
        if "app = FastAPI(" in line or "app=FastAPI(" in line:
            # Find end of FastAPI() call (might be multi-line)
            insert_at = i + 1
            if ")" not in line:
                while insert_at < len(lines) and ")" not in lines[insert_at]:
                    insert_at += 1
                insert_at += 1

            lines.insert(insert_at, "")
            lines.insert(insert_at + 1, "# Middleware (ordered: tracing → CORS → auth → rate_limit → logging)")
            for j, reg in enumerate(middleware_lines):
                lines.insert(insert_at + 2 + j, reg)
            break

    buffer[main_py] = "\n".join(lines)
    return buffer


# ═══════════════════════════════════════════════════════════════════
# PASS 5: Settings Wiring
# ═══════════════════════════════════════════════════════════════════

_ENV_PATTERNS = [
    re.compile(r'os\.getenv\(\s*["\'](\w+)["\']'),
    re.compile(r'os\.environ\[\s*["\'](\w+)["\']'),
    re.compile(r'os\.environ\.get\(\s*["\'](\w+)["\']'),
]

# Type inference for settings fields
_TYPE_HINTS = {
    "PORT": "int",
    "WORKERS": "int",
    "TIMEOUT": "int",
    "TTL": "int",
    "SIZE": "int",
    "MAX": "int",
    "MIN": "int",
    "COUNT": "int",
    "LIMIT": "int",
    "RETRIES": "int",
    "ATTEMPTS": "int",
    "DEBUG": "bool",
    "ENABLED": "bool",
    "VERBOSE": "bool",
}

# Sensible defaults
_SETTING_DEFAULTS = {
    "int": "8000",
    "bool": "False",
    "str": '""',
}


def _infer_type(var_name: str) -> str:
    """Infer the Python type for a settings field based on naming convention."""
    name_upper = var_name.upper()
    for suffix, type_hint in _TYPE_HINTS.items():
        if name_upper.endswith(suffix):
            return type_hint
    if "URL" in name_upper or "URI" in name_upper or "HOST" in name_upper:
        return "str"
    if "KEY" in name_upper or "SECRET" in name_upper or "TOKEN" in name_upper or "PASSWORD" in name_upper:
        return "str"
    return "str"


def _settings_wiring_pass(buffer: dict[str, str], report: WiringReport) -> dict[str, str]:
    """Ensure all env vars are declared in the Settings class."""
    # Collect all env var references
    all_env_vars: set[str] = set()
    for path, content in buffer.items():
        if not path.endswith(".py"):
            continue
        for pattern in _ENV_PATTERNS:
            all_env_vars.update(pattern.findall(content))

    if not all_env_vars:
        return buffer

    # Find or create settings.py
    settings_path = None
    for path in buffer:
        if "settings" in Path(path).stem and path.endswith(".py"):
            if "config" in path or "core" in path or "app" in path:
                settings_path = path
                break

    if not settings_path:
        # Look for any settings file
        for path in buffer:
            if "settings" in Path(path).stem and path.endswith(".py"):
                settings_path = path
                break

    if settings_path:
        # Parse existing settings to find declared fields
        settings_content = buffer[settings_path]
        existing_fields = set(re.findall(r'(\w+)\s*:\s*\w+', settings_content))

        missing = all_env_vars - existing_fields
        if not missing:
            return buffer

        # Add missing fields to Settings class
        lines = settings_content.splitlines()

        # Find the end of the Settings class
        class_end = len(lines)
        in_class = False
        for i, line in enumerate(lines):
            if "class Settings" in line:
                in_class = True
            elif in_class and line and not line.startswith(" ") and not line.startswith("\t"):
                class_end = i
                break

        # Insert fields before class end
        additions = []
        for var in sorted(missing):
            var_type = _infer_type(var)
            var_lower = var.lower()
            default = _SETTING_DEFAULTS.get(var_type, '""')
            additions.append(f"    {var_lower}: {var_type} = {default}")

            report.actions.append(WiringAction(
                pass_name="settings_wiring",
                description=f"Added {var} as {var_type} to Settings class",
                file=settings_path,
            ))

        for addition in reversed(additions):
            lines.insert(class_end, addition)

        buffer[settings_path] = "\n".join(lines)

    else:
        # Generate a new settings.py
        settings_path = "services/api/app/core/settings.py"
        field_lines = []
        for var in sorted(all_env_vars):
            var_type = _infer_type(var)
            var_lower = var.lower()
            default = _SETTING_DEFAULTS.get(var_type, '""')
            field_lines.append(f"    {var_lower}: {var_type} = {default}")

            report.actions.append(WiringAction(
                pass_name="settings_wiring",
                description=f"Created Settings.{var_lower} ({var_type})",
                file=settings_path,
            ))

        buffer[settings_path] = '''"""Application settings — auto-wired by NIKAME."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All environment variables used across the application."""

{fields}

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
'''.format(fields="\n".join(field_lines))

    return buffer


# ═══════════════════════════════════════════════════════════════════
# PASS 6: Import Wiring (Verification)
# ═══════════════════════════════════════════════════════════════════

_IMPORT_PATTERN = re.compile(r'^from\s+([\w.]+)\s+import\s+([\w, ]+)', re.MULTILINE)
_SIMPLE_IMPORT = re.compile(r'^import\s+([\w.]+)', re.MULTILINE)


def _import_wiring_pass(buffer: dict[str, str], report: WiringReport) -> dict[str, str]:
    """Verify all cross-file imports resolve correctly."""
    # Build a module registry from the file buffer
    available_modules: set[str] = set()
    module_exports: dict[str, set[str]] = {}

    for path in buffer:
        if not path.endswith(".py"):
            continue
        # Convert path to module notation
        mod_path = path.replace("/", ".").replace(".py", "")
        available_modules.add(mod_path)

        # Also add parent packages
        parts = mod_path.split(".")
        for i in range(1, len(parts)):
            available_modules.add(".".join(parts[:i]))

        # Collect exports (top-level names defined in the file)
        content = buffer[path]
        # Classes, functions, and variable assignments
        exports = set()
        for m in re.finditer(r'^(?:class|def|async def)\s+(\w+)', content, re.MULTILINE):
            exports.add(m.group(1))
        for m in re.finditer(r'^(\w+)\s*=', content, re.MULTILINE):
            exports.add(m.group(1))
        module_exports[mod_path] = exports

    # Check all imports
    for path, content in buffer.items():
        if not path.endswith(".py"):
            continue

        source_mod = path.replace("/", ".").replace(".py", "")

        # Check from X import Y
        for m in _IMPORT_PATTERN.finditer(content):
            import_module = m.group(1)
            imported_names = [n.strip() for n in m.group(2).split(",")]

            # Skip stdlib and third-party
            top_level = import_module.split(".")[0]
            if top_level in _KNOWN_EXTERNAL:
                continue

            # Only check project-internal imports
            if import_module in available_modules:
                # Check that exported names exist
                exports = module_exports.get(import_module, set())
                for name in imported_names:
                    if name not in exports and exports:  # Only warn if we know the exports
                        report.warnings.append(
                            f"Import '{name}' from '{import_module}' in {path} "
                            f"may not exist (found exports: {', '.join(sorted(exports)[:5])})"
                        )
            elif import_module not in available_modules:
                # Check if it's a project-internal module that doesn't exist
                if any(import_module.startswith(p.split(".")[0]) for p in available_modules):
                    report.warnings.append(
                        f"Module '{import_module}' imported in {path} not found in generated files"
                    )

    return buffer


# Known third-party and stdlib top-level packages to skip in import checks
_KNOWN_EXTERNAL = {
    "os", "sys", "json", "logging", "typing", "pathlib", "datetime",
    "collections", "abc", "asyncio", "contextlib", "dataclasses",
    "enum", "functools", "hashlib", "re", "secrets", "uuid",
    "fastapi", "uvicorn", "sqlalchemy", "alembic", "pydantic",
    "redis", "celery", "httpx", "requests", "structlog", "tenacity",
    "boto3", "minio", "qdrant_client", "langchain", "openai",
    "stripe", "strawberry", "grpc", "prometheus_client",
    "passlib", "jose", "bcrypt", "yaml", "starlette", "jinja2",
    "websockets", "sse_starlette", "slowapi", "confluent_kafka",
    "evidently", "mlflow", "prefect", "pydantic_settings",
    "__future__", "copy", "io", "itertools", "math", "time",
    "subprocess", "tempfile", "textwrap", "threading", "traceback",
    "unittest", "urllib", "warnings", "base64", "csv", "socket",
    "signal", "shutil", "inspect", "importlib", "glob", "random",
    "string", "multiprocessing", "concurrent", "configparser",
    "contextlib",
}


# ═══════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════

class AutoWiringEngine:
    """Runs all wiring passes in order against the file buffer.

    Usage:
        engine = AutoWiringEngine()
        buffer, report = engine.run(file_buffer)
    """

    _PASSES = [
        ("Router Wiring", _router_wiring_pass),
        ("Lifespan Wiring", _lifespan_wiring_pass),
        ("Health Check Wiring", _health_check_wiring_pass),
        ("Middleware Wiring", _middleware_wiring_pass),
        ("Settings Wiring", _settings_wiring_pass),
        ("Import Wiring", _import_wiring_pass),
    ]

    def run(self, file_buffer: dict[str, str]) -> tuple[dict[str, str], WiringReport]:
        """Execute all wiring passes in order.

        Args:
            file_buffer: Dict of relative_path -> content.

        Returns:
            Tuple of (wired_buffer, wiring_report).
        """
        report = WiringReport()

        console.print("\n[bold magenta]━━━ NIKAME Auto-Wiring Engine ━━━[/bold magenta]\n")

        for pass_name, pass_fn in self._PASSES:
            buffer_before = len(file_buffer)
            file_buffer = pass_fn(file_buffer, report)

            # Count actions from this pass
            pass_actions = [a for a in report.actions if a.pass_name == pass_name.lower().replace(" ", "_")]
            count = len(pass_actions)

            if count > 0:
                console.print(f"  [green]⚡ {pass_name}[/green]: {count} connection(s) wired")
                for action in pass_actions:
                    console.print(f"    [dim]→ {action.description}[/dim]")
            else:
                console.print(f"  [dim]○ {pass_name}[/dim]: nothing to wire")

        # Print warnings
        if report.warnings:
            console.print(f"\n  [yellow]⚠ {len(report.warnings)} warning(s):[/yellow]")
            for w in report.warnings:
                console.print(f"    [yellow]{w}[/yellow]")

        console.print(f"\n[bold magenta]✓ Auto-wiring complete. {report.total_actions} total connections made.[/bold magenta]\n")

        return file_buffer, report
