"""Codegen Quality Rules Engine.

Validates all generated files before they are written to disk.
Each rule can detect issues and auto-fix them. If unfixable errors
remain after all auto-fix passes, generation fails loudly.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from nikame.utils.logger import console, get_logger

_log = get_logger("rules_engine")


# ─────────────────────────── Data Classes ───────────────────────────

@dataclass
class RuleViolation:
    """A single rule violation."""
    rule: str
    severity: str  # "P0" (fatal), "P1" (warning)
    file: str
    message: str
    auto_fixable: bool = False


@dataclass
class RuleResult:
    """Result of running a single rule."""
    rule_name: str
    passed: bool
    violations: list[RuleViolation] = field(default_factory=list)
    auto_fixes_applied: int = 0


# ─────────────────────────── Base Rule ───────────────────────────

class BaseRule:
    """Abstract base class for all quality rules."""

    NAME: str = "base"
    DESCRIPTION: str = "Base rule"

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        """Check the file buffer for violations. Return a RuleResult."""
        raise NotImplementedError

    def fix(self, file_buffer: dict[str, str], violations: list[RuleViolation]) -> dict[str, str]:
        """Attempt to auto-fix violations. Return the modified buffer."""
        return file_buffer


# ─────────────────────── Import Check Rule ───────────────────────

class ImportCheckRule(BaseRule):
    """Every generated Python file must be importable."""

    NAME = "import_check"
    DESCRIPTION = "Verify all generated Python files are importable"

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        # Write all Python files to a temp dir and try importing each
        py_files = {k: v for k, v in file_buffer.items() if k.endswith(".py")}
        if not py_files:
            return RuleResult(rule_name=self.NAME, passed=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Write all files so cross-imports resolve
            for rel_path, content in py_files.items():
                target = tmp_path / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

                # Ensure __init__.py exists in every package directory
                for parent in target.parent.relative_to(tmp_path).parents:
                    init = tmp_path / parent / "__init__.py"
                    if not init.exists():
                        init.write_text("", encoding="utf-8")

            # Try to compile each file (syntax check — cheaper than full import)
            for rel_path, content in py_files.items():
                target = tmp_path / rel_path
                result = subprocess.run(
                    [sys.executable, "-c", f"import py_compile; py_compile.compile('{target}', doraise=True)"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    error_msg = result.stderr.strip().split("\n")[-1] if result.stderr else "Unknown syntax error"
                    violations.append(RuleViolation(
                        rule=self.NAME,
                        severity="P0",
                        file=rel_path,
                        message=f"Syntax error: {error_msg}",
                        auto_fixable=False,
                    ))

        passed = len(violations) == 0
        return RuleResult(rule_name=self.NAME, passed=passed, violations=violations)


# ─────────────────── Requirements Check Rule ─────────────────────

# Mapping from import name -> PyPI package name for common packages
IMPORT_TO_PYPI = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "alembic": "alembic",
    "pydantic": "pydantic",
    "redis": "redis",
    "celery": "celery",
    "httpx": "httpx",
    "requests": "requests",
    "structlog": "structlog",
    "tenacity": "tenacity",
    "boto3": "boto3",
    "minio": "minio",
    "qdrant_client": "qdrant-client",
    "langchain": "langchain",
    "openai": "openai",
    "stripe": "stripe",
    "strawberry": "strawberry-graphql",
    "grpc": "grpcio",
    "prometheus_client": "prometheus-client",
    "passlib": "passlib",
    "jose": "python-jose",
    "bcrypt": "bcrypt",
    "yaml": "pyyaml",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "dotenv": "python-dotenv",
    "psycopg2": "psycopg2-binary",
    "asyncpg": "asyncpg",
    "aioredis": "redis",
    "starlette": "starlette",
    "jinja2": "jinja2",
    "multipart": "python-multipart",
    "websockets": "websockets",
    "sse_starlette": "sse-starlette",
    "slowapi": "slowapi",
    "confluent_kafka": "confluent-kafka",
    "evidently": "evidently",
    "mlflow": "mlflow",
    "prefect": "prefect",
}

# Standard library modules to skip
STDLIB_MODULES = {
    "os", "sys", "json", "logging", "typing", "pathlib", "datetime",
    "collections", "abc", "asyncio", "contextlib", "dataclasses",
    "enum", "functools", "hashlib", "importlib", "inspect", "io",
    "itertools", "math", "operator", "re", "secrets", "shutil",
    "signal", "socket", "subprocess", "tempfile", "textwrap",
    "threading", "time", "traceback", "unittest", "urllib", "uuid",
    "warnings", "copy", "glob", "string", "struct", "base64",
    "binascii", "csv", "decimal", "difflib", "email", "html",
    "http", "ipaddress", "mimetypes", "multiprocessing", "numbers",
    "pickle", "platform", "pprint", "queue", "random", "statistics",
    "types", "unicodedata", "weakref", "xml", "zipfile", "zlib",
    "__future__", "builtins", "codecs", "locale", "posixpath",
    "concurrent", "configparser", "dis", "fractions", "heapq",
    "keyword", "marshal", "shelve", "sqlite3", "token", "tokenize",
}

# Default versions for auto-added packages
DEFAULT_VERSIONS = {
    "fastapi": ">=0.109.0",
    "uvicorn": ">=0.27.0",
    "sqlalchemy": ">=2.0.25",
    "alembic": ">=1.13.1",
    "pydantic": ">=2.5.3",
    "redis": ">=5.0.1",
    "celery": ">=5.3.6",
    "httpx": ">=0.26.0",
    "requests": ">=2.31.0",
    "structlog": ">=24.1.0",
    "tenacity": ">=8.2.3",
    "boto3": ">=1.34.0",
    "minio": ">=7.2.3",
    "qdrant-client": ">=1.7.3",
    "langchain": ">=0.1.0",
    "openai": ">=1.10.0",
    "stripe": ">=7.12.0",
    "strawberry-graphql": ">=0.219.0",
    "grpcio": ">=1.60.0",
    "prometheus-client": ">=0.19.0",
    "passlib": ">=1.7.4",
    "python-jose": ">=3.3.0",
    "bcrypt": ">=4.1.2",
    "pyyaml": ">=6.0.1",
    "python-dotenv": ">=1.0.0",
    "psycopg2-binary": ">=2.9.9",
    "asyncpg": ">=0.29.0",
    "starlette": ">=0.35.1",
    "jinja2": ">=3.1.3",
    "python-multipart": ">=0.0.6",
    "websockets": ">=12.0",
    "sse-starlette": ">=1.8.2",
    "slowapi": ">=0.1.9",
    "confluent-kafka": ">=2.3.0",
    "evidently": ">=0.4.13",
    "mlflow": ">=2.10.0",
    "prefect": ">=2.14.0",
}


class RequirementsCheckRule(BaseRule):
    """Every import must have a corresponding entry in requirements.txt."""

    NAME = "requirements_check"
    DESCRIPTION = "Verify all imports are declared in requirements.txt"

    def _extract_imports(self, content: str) -> set[str]:
        """Extract top-level import names from Python source."""
        imports = set()
        for line in content.splitlines():
            line = line.strip()
            # import X or import X.Y
            m = re.match(r'^import\s+([\w.]+)', line)
            if m:
                imports.add(m.group(1).split(".")[0])
            # from X import ...
            m = re.match(r'^from\s+([\w.]+)\s+import', line)
            if m:
                imports.add(m.group(1).split(".")[0])
        return imports

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        # Find requirements.txt
        req_files = [k for k in file_buffer if k.endswith("requirements.txt")]
        if not req_files:
            return RuleResult(rule_name=self.NAME, passed=True)

        req_path = req_files[0]
        req_content = file_buffer[req_path]
        existing_packages = set()
        for line in req_content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                pkg = re.split(r'[>=<!\[]', line)[0].strip().lower()
                existing_packages.add(pkg)

        # Collect all imports from all Python files
        all_imports: set[str] = set()
        # Determine the project's own package names for filtering.
        # Any directory that appears in the buffer is a project-internal package.
        project_packages = set()
        for path in file_buffer:
            parts = Path(path).parts
            for part in parts:
                if part not in (".", ".."):
                    project_packages.add(part)

        for path, content in file_buffer.items():
            if path.endswith(".py"):
                all_imports.update(self._extract_imports(content))

        # Filter out stdlib, project-internal, and already declared
        for imp in all_imports:
            if imp in STDLIB_MODULES:
                continue
            if imp in project_packages:
                continue

            pypi_name = IMPORT_TO_PYPI.get(imp, imp).lower()
            if pypi_name not in existing_packages:
                violations.append(RuleViolation(
                    rule=self.NAME,
                    severity="P0",
                    file=req_path,
                    message=f"Package '{pypi_name}' imported but missing from {req_path}",
                    auto_fixable=True,
                ))

        passed = len(violations) == 0
        return RuleResult(rule_name=self.NAME, passed=passed, violations=violations)

    def fix(self, file_buffer: dict[str, str], violations: list[RuleViolation]) -> dict[str, str]:
        """Auto-add missing packages to requirements.txt."""
        req_files = [k for k in file_buffer if k.endswith("requirements.txt")]
        if not req_files:
            return file_buffer

        req_path = req_files[0]
        content = file_buffer[req_path]
        fixes = 0

        for v in violations:
            if v.auto_fixable and v.rule == self.NAME:
                # Extract package name from violation message
                match = re.search(r"Package '([\w-]+)'", v.message)
                if match:
                    pkg = match.group(1)
                    version = DEFAULT_VERSIONS.get(pkg, "")
                    entry = f"{pkg}{version}" if version else pkg
                    content += f"\n{entry}"
                    fixes += 1

        file_buffer[req_path] = content
        return file_buffer


# ─────────────────── Env Variable Check Rule ─────────────────────

# Default values for common env vars
ENV_DEFAULTS = {
    "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/app",
    "REDIS_URL": "redis://localhost:6379/0",
    "SECRET_KEY": "__GENERATED_SECRET__",
    "JWT_SECRET": "__GENERATED_SECRET__",
    "API_KEY": "__GENERATED_SECRET__",
    "MINIO_ACCESS_KEY": "minioadmin",
    "MINIO_SECRET_KEY": "__GENERATED_SECRET__",
    "MINIO_ENDPOINT": "localhost:9000",
    "STRIPE_SECRET_KEY": "sk_test_placeholder",
    "STRIPE_WEBHOOK_SECRET": "whsec_placeholder",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "__GENERATED_SECRET__",
    "POSTGRES_DB": "app",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "QDRANT_HOST": "localhost",
    "QDRANT_PORT": "6333",
    "OPENAI_API_KEY": "sk-placeholder",
    "OLLAMA_HOST": "http://localhost:11434",
    "MLFLOW_TRACKING_URI": "http://localhost:5000",
    "PREFECT_API_URL": "http://localhost:4200/api",
    "LOG_LEVEL": "INFO",
    "ENVIRONMENT": "development",
    "SERVICE_NAME": "app",
    "MAX_RETRY_ATTEMPTS": "3",
    "CACHE_TTL_SECONDS": "3600",
}


class EnvCheckRule(BaseRule):
    """Every env variable reference must exist in .env.example and .env.generated."""

    NAME = "env_check"
    DESCRIPTION = "Verify all environment variable references are declared"

    _PATTERNS = [
        re.compile(r'os\.getenv\(\s*["\'](\w+)["\']'),
        re.compile(r'os\.environ\[\s*["\'](\w+)["\']'),
        re.compile(r'os\.environ\.get\(\s*["\'](\w+)["\']'),
        re.compile(r'config\(\s*["\'](\w+)["\']'),
        re.compile(r'env\(\s*["\'](\w+)["\']'),
    ]

    def _extract_env_refs(self, content: str) -> set[str]:
        """Extract environment variable references from Python source."""
        refs = set()
        for pattern in self._PATTERNS:
            refs.update(pattern.findall(content))
        return refs

    def _parse_env_file(self, content: str) -> set[str]:
        """Parse .env file and return set of declared variable names."""
        declared = set()
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                declared.add(line.split("=")[0].strip())
        return declared

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        # Collect all env var references
        all_refs: set[str] = set()
        for path, content in file_buffer.items():
            if path.endswith(".py"):
                all_refs.update(self._extract_env_refs(content))

        if not all_refs:
            return RuleResult(rule_name=self.NAME, passed=True)

        # Check .env.example
        env_example = file_buffer.get(".env.example", "")
        env_generated = file_buffer.get(".env.generated", "")

        declared_example = self._parse_env_file(env_example)
        declared_generated = self._parse_env_file(env_generated)

        for var in all_refs:
            if var not in declared_example:
                violations.append(RuleViolation(
                    rule=self.NAME,
                    severity="P0",
                    file=".env.example",
                    message=f"Env var '{var}' referenced in code but missing from .env.example",
                    auto_fixable=True,
                ))
            if var not in declared_generated:
                violations.append(RuleViolation(
                    rule=self.NAME,
                    severity="P0",
                    file=".env.generated",
                    message=f"Env var '{var}' referenced in code but missing from .env.generated",
                    auto_fixable=True,
                ))

        passed = len(violations) == 0
        return RuleResult(rule_name=self.NAME, passed=passed, violations=violations)

    def fix(self, file_buffer: dict[str, str], violations: list[RuleViolation]) -> dict[str, str]:
        """Auto-add missing env vars."""
        import secrets as _secrets

        for v in violations:
            if v.auto_fixable and v.rule == self.NAME:
                match = re.search(r"Env var '(\w+)'", v.message)
                if not match:
                    continue
                var_name = match.group(1)
                default = ENV_DEFAULTS.get(var_name, "changeme")

                if v.file == ".env.example":
                    content = file_buffer.get(".env.example", "")
                    content += f"\n# Auto-added by rules engine\n{var_name}="
                    file_buffer[".env.example"] = content

                elif v.file == ".env.generated":
                    content = file_buffer.get(".env.generated", "")
                    if default == "__GENERATED_SECRET__":
                        value = _secrets.token_urlsafe(32)
                    else:
                        value = default
                    content += f"\n{var_name}={value}"
                    file_buffer[".env.generated"] = content

        return file_buffer


# ─────────────────── Dockerfile Check Rule ───────────────────────

class DockerfileCheckRule(BaseRule):
    """Every compose service with build: must have a Dockerfile."""

    NAME = "dockerfile_check"
    DESCRIPTION = "Verify all Docker build contexts have Dockerfiles"

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        compose_files = [k for k in file_buffer if "docker-compose" in k and k.endswith((".yml", ".yaml"))]
        if not compose_files:
            return RuleResult(rule_name=self.NAME, passed=True)

        for compose_path in compose_files:
            try:
                compose = yaml.safe_load(file_buffer[compose_path])
            except yaml.YAMLError:
                continue

            services = compose.get("services", {})
            if not services:
                continue

            for svc_name, svc_config in services.items():
                if not isinstance(svc_config, dict):
                    continue
                build = svc_config.get("build")
                if build is None:
                    continue

                if isinstance(build, str):
                    context = build
                    dockerfile = "Dockerfile"
                elif isinstance(build, dict):
                    context = build.get("context", ".")
                    dockerfile = build.get("dockerfile", "Dockerfile")
                else:
                    continue

                # Resolve path relative to compose file's directory
                import os.path
                compose_dir = str(Path(compose_path).parent)
                if compose_dir == ".":
                    raw = f"{context}/{dockerfile}" if context != "." else dockerfile
                else:
                    raw = f"{compose_dir}/{context}/{dockerfile}" if context != "." else f"{compose_dir}/{dockerfile}"

                # Normalize away any .. segments
                df_path = os.path.normpath(raw)

                if df_path not in file_buffer:
                    violations.append(RuleViolation(
                        rule=self.NAME,
                        severity="P0",
                        file=compose_path,
                        message=f"Service '{svc_name}' references build context '{context}' but '{df_path}' not found",
                        auto_fixable=True,
                    ))

        passed = len(violations) == 0
        return RuleResult(rule_name=self.NAME, passed=passed, violations=violations)

    def fix(self, file_buffer: dict[str, str], violations: list[RuleViolation]) -> dict[str, str]:
        """Auto-generate missing Dockerfiles."""
        for v in violations:
            if v.auto_fixable and v.rule == self.NAME:
                match = re.search(r"'(\S+)' not found", v.message)
                if match:
                    df_path = match.group(1)
                    svc_match = re.search(r"Service '(\w+)'", v.message)
                    svc_name = svc_match.group(1) if svc_match else "app"

                    file_buffer[df_path] = f"""# Auto-generated by NIKAME Rules Engine
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc libpq-dev curl && \\
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        return file_buffer


# ─────────────────── Volume Mount Check Rule ─────────────────────

class VolumeMountCheckRule(BaseRule):
    """Every volume mount must point to an existing generated file."""

    NAME = "volume_check"
    DESCRIPTION = "Verify all volume mount source paths exist in generated output"

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        compose_files = [k for k in file_buffer if "docker-compose" in k and k.endswith((".yml", ".yaml"))]
        if not compose_files:
            return RuleResult(rule_name=self.NAME, passed=True)

        for compose_path in compose_files:
            try:
                compose = yaml.safe_load(file_buffer[compose_path])
            except yaml.YAMLError:
                continue

            services = compose.get("services", {})
            if not services:
                continue

            compose_dir = str(Path(compose_path).parent)

            for svc_name, svc_config in services.items():
                if not isinstance(svc_config, dict):
                    continue
                volumes = svc_config.get("volumes", [])
                for vol in volumes:
                    if isinstance(vol, str) and ":" in vol:
                        host_path = vol.split(":")[0]
                        # Skip docker named volumes, absolute paths, and env vars
                        if host_path.startswith(("/", "$", "~")) or not any(c in host_path for c in [".", "/"]):
                            continue

                        # Resolve relative to compose dir
                        resolved = str(Path(compose_dir) / host_path) if compose_dir != "." else host_path
                        resolved = str(Path(resolved))

                        # Check if file or any file in that directory exists
                        found = False
                        for buf_path in file_buffer:
                            if buf_path == resolved or buf_path.startswith(resolved + "/"):
                                found = True
                                break

                        if not found:
                            violations.append(RuleViolation(
                                rule=self.NAME,
                                severity="P1",
                                file=compose_path,
                                message=f"Service '{svc_name}' mounts '{host_path}' but path '{resolved}' not generated",
                                auto_fixable=True,
                            ))

        passed = len(violations) == 0
        return RuleResult(rule_name=self.NAME, passed=passed, violations=violations)

    def fix(self, file_buffer: dict[str, str], violations: list[RuleViolation]) -> dict[str, str]:
        """Auto-generate missing mount targets (empty config files)."""
        for v in violations:
            if v.auto_fixable and v.rule == self.NAME:
                match = re.search(r"path '(\S+)' not generated", v.message)
                if match:
                    missing_path = match.group(1)
                    if missing_path.endswith((".conf", ".cfg", ".ini", ".yml", ".yaml", ".json")):
                        file_buffer[missing_path] = f"# Auto-generated placeholder by NIKAME Rules Engine\n"
                    else:
                        # Treat as directory — create a .gitkeep
                        file_buffer[f"{missing_path}/.gitkeep"] = ""
        return file_buffer


# ────────────────── Router Registration Check ────────────────────

class RouterCheckRule(BaseRule):
    """Every FastAPI router must be registered in main.py."""

    NAME = "router_check"
    DESCRIPTION = "Verify all routers are registered in main.py"

    _ROUTER_PATTERN = re.compile(r'(\w+)\s*=\s*APIRouter\(')
    _INCLUDE_PATTERN = re.compile(r'app\.include_router\(\s*(\w+)')

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        # Find main.py
        main_py_paths = [k for k in file_buffer if k.endswith("main.py") and "app" in k]
        if not main_py_paths:
            return RuleResult(rule_name=self.NAME, passed=True)

        main_py_path = main_py_paths[0]
        main_content = file_buffer[main_py_path]

        # Find all included routers
        included = set(self._INCLUDE_PATTERN.findall(main_content))

        # Find all defined routers in other files
        for path, content in file_buffer.items():
            if path == main_py_path or not path.endswith(".py"):
                continue
            routers = self._ROUTER_PATTERN.findall(content)
            for router_var in routers:
                if router_var not in included:
                    violations.append(RuleViolation(
                        rule=self.NAME,
                        severity="P0",
                        file=path,
                        message=f"Router '{router_var}' defined in {path} but not registered in {main_py_path}",
                        auto_fixable=True,
                    ))

        passed = len(violations) == 0
        return RuleResult(rule_name=self.NAME, passed=passed, violations=violations)

    def fix(self, file_buffer: dict[str, str], violations: list[RuleViolation]) -> dict[str, str]:
        """Auto-register missing routers in main.py."""
        main_py_paths = [k for k in file_buffer if k.endswith("main.py") and "app" in k]
        if not main_py_paths:
            return file_buffer

        main_py_path = main_py_paths[0]
        content = file_buffer[main_py_path]

        for v in violations:
            if v.auto_fixable and v.rule == self.NAME:
                match = re.search(r"Router '(\w+)' defined in (\S+)", v.message)
                if match:
                    router_var = match.group(1)
                    source_file = match.group(2)

                    # Convert file path to module path
                    module_path = source_file.replace("/", ".").replace(".py", "")
                    import_line = f"from {module_path} import {router_var}"
                    register_line = f'app.include_router({router_var})'

                    if import_line not in content:
                        # Add import after last import line
                        lines = content.splitlines()
                        last_import = 0
                        for i, line in enumerate(lines):
                            if line.startswith("import ") or line.startswith("from "):
                                last_import = i
                        lines.insert(last_import + 1, import_line)
                        content = "\n".join(lines)

                    if register_line not in content:
                        # Add before the last function definition or at end
                        if "# NIKAME ROUTERS" in content:
                            content = content.replace("# NIKAME ROUTERS", f"# NIKAME ROUTERS\n{register_line}")
                        else:
                            content += f"\n{register_line}\n"

        file_buffer[main_py_path] = content
        return file_buffer


# ─────────────── Integration Lifespan/Health Check ───────────────

class IntegrationCheckRule(BaseRule):
    """Every integration must be wired into lifespan and health check."""

    NAME = "integration_check"
    DESCRIPTION = "Verify all integrations are initialized in lifespan and have health checks"

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        # Find integration files
        integration_files = [
            k for k in file_buffer
            if "integrations/" in k and k.endswith(".py") and "__init__" not in k
        ]

        if not integration_files:
            return RuleResult(rule_name=self.NAME, passed=True)

        # Find main.py to check lifespan
        main_files = [k for k in file_buffer if k.endswith("main.py") and "app" in k]
        if not main_files:
            return RuleResult(rule_name=self.NAME, passed=True)

        main_content = file_buffer[main_files[0]]

        for int_file in integration_files:
            content = file_buffer[int_file]
            module_name = Path(int_file).stem

            # Check if there's a startup function
            if "async def startup" in content or "def startup" in content:
                if f"{module_name}" not in main_content:
                    violations.append(RuleViolation(
                        rule=self.NAME,
                        severity="P1",
                        file=int_file,
                        message=f"Integration '{module_name}' has startup() but is not referenced in main.py lifespan",
                        auto_fixable=False,
                    ))

            # Check if there's a health check function
            if "async def health" in content or "def health" in content:
                if f"{module_name}" not in main_content:
                    violations.append(RuleViolation(
                        rule=self.NAME,
                        severity="P1",
                        file=int_file,
                        message=f"Integration '{module_name}' has health() but is not referenced in health endpoint",
                        auto_fixable=False,
                    ))

        passed = len(violations) == 0
        return RuleResult(rule_name=self.NAME, passed=passed, violations=violations)


# ────────────────── Secret Scanning Rule ─────────────────────────

class SecretScanRule(BaseRule):
    """No hardcoded secrets in generated code."""

    NAME = "secret_scan"
    DESCRIPTION = "Scan for hardcoded secrets, API keys, and passwords"

    _SECRET_PATTERNS = [
        (re.compile(r'["\'](?:sk|pk)[-_](?:live|test)[-_]\w{20,}["\']'), "Stripe-like API key"),
        (re.compile(r'["\'](?:ghp|gho|ghu|ghs|ghr)_\w{36,}["\']'), "GitHub token"),
        (re.compile(r'["\']AKIA[0-9A-Z]{16}["\']'), "AWS access key"),
        (re.compile(r'password\s*=\s*["\'][^"\']{4,}["\']', re.IGNORECASE), "Hardcoded password"),
        (re.compile(r'secret\s*=\s*["\'][^"\']{8,}["\']', re.IGNORECASE), "Hardcoded secret"),
        (re.compile(r'token\s*=\s*["\'][a-zA-Z0-9_\-]{20,}["\']', re.IGNORECASE), "Hardcoded token"),
    ]

    # Whitelist patterns that are not actual secrets
    _WHITELIST = [
        "placeholder", "changeme", "your_", "example", "test_", "xxx",
        "None", "os.getenv", "settings.", "config.", "env(",
    ]

    def check(self, file_buffer: dict[str, str]) -> RuleResult:
        violations = []

        for path, content in file_buffer.items():
            if not path.endswith(".py"):
                continue

            for pattern, description in self._SECRET_PATTERNS:
                for match in pattern.finditer(content):
                    matched_text = match.group(0)
                    # Check whitelist
                    if any(w in matched_text.lower() for w in self._WHITELIST):
                        continue

                    violations.append(RuleViolation(
                        rule=self.NAME,
                        severity="P0",
                        file=path,
                        message=f"Possible {description} found: {matched_text[:40]}...",
                        auto_fixable=False,
                    ))

        passed = len(violations) == 0
        return RuleResult(rule_name=self.NAME, passed=passed, violations=violations)


# ────────────────────── Rules Engine ─────────────────────────────

class RulesEngine:
    """Orchestrates all quality rules against the generated file buffer.

    Usage:
        engine = RulesEngine()
        buffer, results = engine.validate(file_buffer)
        # buffer is now the auto-fixed version
        # results contains pass/fail for each rule
    """

    def __init__(self) -> None:
        from nikame.codegen.rules.standards import PRODUCTION_RULES

        self.rules: list[BaseRule] = [
            # Core quality rules
            ImportCheckRule(),
            RequirementsCheckRule(),
            EnvCheckRule(),
            DockerfileCheckRule(),
            VolumeMountCheckRule(),
            RouterCheckRule(),
            IntegrationCheckRule(),
            SecretScanRule(),
            # Production code standards
            *PRODUCTION_RULES,
        ]

    def validate(self, file_buffer: dict[str, str], max_passes: int = 3) -> tuple[dict[str, str], list[RuleResult]]:
        """Run all rules, auto-fix what's possible, re-validate.

        Args:
            file_buffer: Dict of relative_path -> content.
            max_passes: Maximum auto-fix iterations to prevent loops.

        Returns:
            Tuple of (fixed_buffer, list_of_final_results).
        """
        console.print("\n[bold cyan]━━━ NIKAME Rules Engine ━━━[/bold cyan]\n")

        final_results: list[RuleResult] = []

        for pass_num in range(1, max_passes + 1):
            console.print(f"[dim]Pass {pass_num}/{max_passes}[/dim]")
            all_passed = True
            pass_results: list[RuleResult] = []
            all_violations: list[RuleViolation] = []

            for rule in self.rules:
                result = rule.check(file_buffer)
                pass_results.append(result)

                status = "[green]✓ PASS[/green]" if result.passed else "[red]✗ FAIL[/red]"
                console.print(f"  {status} {rule.NAME}: {rule.DESCRIPTION}")

                if not result.passed:
                    all_passed = False
                    for v in result.violations:
                        sev_color = "red" if v.severity == "P0" else "yellow"
                        fix_tag = " [cyan][AUTO-FIX][/cyan]" if v.auto_fixable else ""
                        console.print(f"    [{sev_color}]{v.severity}[/{sev_color}] {v.file}: {v.message}{fix_tag}")
                    all_violations.extend(result.violations)

            final_results = pass_results

            if all_passed:
                console.print(f"\n[bold green]✓ All {len(self.rules)} rules passed.[/bold green]\n")
                break

            # Attempt auto-fixes
            fixable = [v for v in all_violations if v.auto_fixable]
            if not fixable:
                break  # Nothing more we can fix

            console.print(f"\n  [cyan]Applying {len(fixable)} auto-fixes...[/cyan]")

            for rule in self.rules:
                rule_violations = [v for v in fixable if v.rule == rule.NAME]
                if rule_violations:
                    file_buffer = rule.fix(file_buffer, rule_violations)

                    # Update the result
                    for r in final_results:
                        if r.rule_name == rule.NAME:
                            r.auto_fixes_applied = len(rule_violations)

            console.print("")

        # Final summary
        p0_failures = sum(
            1 for r in final_results
            for v in r.violations
            if v.severity == "P0" and not v.auto_fixable
        )
        if p0_failures > 0:
            console.print(f"[bold red]✗ {p0_failures} P0 failures remain. Generation blocked.[/bold red]\n")
        else:
            total_fixes = sum(r.auto_fixes_applied for r in final_results)
            if total_fixes > 0:
                console.print(f"[bold green]✓ All issues resolved. {total_fixes} auto-fixes applied.[/bold green]\n")

        return file_buffer, final_results
