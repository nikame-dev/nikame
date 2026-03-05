"""FastAPI application module.

Generates a Docker Compose service for a FastAPI application
with uvicorn workers, health checks, and proper env var wiring.
"""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class FastAPIModule(BaseModule):
    """FastAPI web framework module.

    Generates a containerized FastAPI service with:
    - Auto-configured uvicorn workers
    - Health check endpoint
    - CORS middleware configuration
    - Environment variable wiring to all backend services
    """

    NAME = "fastapi"
    CATEGORY = "api"
    DESCRIPTION = "FastAPI web framework with uvicorn ASGI server"
    DEFAULT_VERSION = "0.109"
    DEPENDENCIES: list[str] = []
    CONFLICTS: list[str] = []

    def __init__(self, config: dict[str, Any], ctx: ModuleContext) -> None:
        super().__init__(config, ctx)
        workers_val = config.get("workers", "auto")
        self.workers: int = 4 if workers_val == "auto" else int(workers_val)
        self.cors_origins: list[str] = config.get("cors_origins", ["*"])
        self.port: int = config.get("port", 8000)

    def compose_spec(self) -> dict[str, Any]:
        """Generate Docker Compose service spec for FastAPI."""
        return {
            "api": {
                "build": {
                    "context": "../app",
                    "dockerfile": "Dockerfile",
                },
                "restart": "unless-stopped",
                "ports": [f"{self.port}:{self.port}"],
                "environment": {
                    "APP_NAME": self.ctx.project_name,
                    "APP_ENV": self.ctx.environment,
                    "UVICORN_WORKERS": str(self.workers),
                    "UVICORN_PORT": str(self.port),
                    "CORS_ORIGINS": ",".join(self.cors_origins),
                    **self.ctx.all_env_vars,
                },
                "healthcheck": self.health_check(),
                "networks": [f"{self.ctx.project_name}_network"],
                "labels": {
                    "nikame.module": "fastapi",
                    "nikame.category": "api",
                },
            }
        }

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate full production-ready K8s architecture for FastAPI."""
        name = "api"
        image = f"{self.ctx.project_name}-{name}:latest"

        manifests: list[dict[str, Any]] = []

        # 1. Service Account
        manifests.append(self.service_account(name))

        # 2. ConfigMap
        manifests.append(self.config_map(name, {"APP_ENV": self.ctx.environment, "PORT": str(self.port)}))

        # 3. Deployment
        deployment: dict[str, Any] = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": name,
                "namespace": self.ctx.namespace,
                "labels": {"app": name, "nikame.module": self.NAME},
            },
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"app": name}},
                "template": {
                    "metadata": {"labels": {"app": name}},
                    "spec": {
                        "serviceAccountName": name,
                        "initContainers": [
                            self.init_container_wait("postgres", 5432)
                        ],
                        "containers": [
                            {
                                "name": name,
                                "image": f"{self.ctx.project_name}-api:latest",
                                "ports": [{"containerPort": 8000}],
                                "envFrom": [{"configMapRef": {"name": name}}],
                                "resources": self.resource_requirements(),
                                "livenessProbe": {
                                    "httpGet": {"path": "/health", "port": self.port},
                                    "initialDelaySeconds": 10,
                                    "periodSeconds": 30,
                                },
                                "readinessProbe": {
                                    "httpGet": {"path": "/health", "port": self.port},
                                    "initialDelaySeconds": 5,
                                    "periodSeconds": 10,
                                },
                            }
                        ]
                    },
                },
            },
        }

        # 2. Service
        service: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": name,
                "namespace": self.ctx.namespace,
                "labels": {"app": name}
            },
            "spec": {
                "selector": {"app": name},
                "ports": [{"port": 80, "targetPort": self.port}],
                "type": "ClusterIP",
            },
        }

        # 3. Production Manifests
        manifests = [
            self.service_account(name),
            self.config_map(f"{name}-config", {"APP_ENV": self.ctx.environment, "PORT": str(self.port)}),
            deployment,
            service,
            self.network_policy(name, allow_from=["ingress-nginx", "traefik"]), # Basic whitelist
            self.hpa(name, min_reps=2, max_reps=10),
            self.pdb(name),
        ]

        if self.ctx.domain:
            manifests.append(self.ingress(name, self.ctx.domain, service_port=80, tls_secret=f"{name}-tls"))

        return manifests

    def health_check(self) -> dict[str, Any]:
        """Docker Compose health check — hits /health endpoint."""
        return {
            "test": ["CMD", "curl", "-f", f"http://localhost:{self.port}/health"],
            "interval": "15s",
            "timeout": "5s",
            "retries": 3,
            "start_period": "10s",
        }

    def env_vars(self) -> dict[str, str]:
        """Expose API URL for other services."""
        return {
            "API_URL": f"http://api:{self.port}",
        }

    def prometheus_rules(self) -> list[dict[str, Any]]:
        """Prometheus alert rules for the FastAPI service."""
        return [
            {
                "alert": "APIHighLatency",
                "expr": 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="api"}[5m])) > 1',
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {
                    "summary": "API p95 latency above 1 second",
                    "description": "FastAPI p95 latency has been above 1s for 5 minutes.",
                },
            },
            {
                "alert": "APIHighErrorRate",
                "expr": 'rate(http_requests_total{service="api",status=~"5.."}[5m]) / rate(http_requests_total{service="api"}[5m]) > 0.05',
                "for": "5m",
                "labels": {"severity": "critical"},
                "annotations": {
                    "summary": "API error rate above 5%",
                    "description": "FastAPI is returning >5% server errors.",
                },
            },
            {
                "alert": "APIDown",
                "expr": 'up{job="api"} == 0',
                "for": "1m",
                "labels": {"severity": "critical"},
                "annotations": {
                    "summary": "FastAPI service is down",
                    "description": "FastAPI has been unreachable for over 1 minute.",
                },
            },
        ]

    def grafana_dashboard(self) -> dict[str, Any] | None:
        """Grafana dashboard for FastAPI metrics."""
        return {
            "title": f"{self.ctx.project_name} — FastAPI",
            "uid": "nikame-fastapi",
            "panels": [
                {
                    "title": "Request Rate",
                    "type": "timeseries",
                    "targets": [{"expr": 'rate(http_requests_total{service="api"}[5m])'}],
                },
                {
                    "title": "p95 Latency",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="api"}[5m]))'
                        }
                    ],
                },
                {
                    "title": "Error Rate",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": 'rate(http_requests_total{service="api",status=~"5.."}[5m]) / rate(http_requests_total{service="api"}[5m])'
                        }
                    ],
                },
                {
                    "title": "Active Connections",
                    "type": "gauge",
                    "targets": [{"expr": 'uvicorn_active_connections{service="api"}'}],
                },
            ],
        }

    def compute_cost_monthly_usd(self) -> float | None:
        """Estimate monthly compute cost."""
        # Rough ECS Fargate cost: 0.5 vCPU, 1GB RAM per worker
        return 25.0 * self.workers

    def resource_requirements(self) -> dict[str, Any]:
        """K8s resource requests and limits."""
        return {
            "requests": {"cpu": "250m", "memory": "512Mi"},
            "limits": {"cpu": "1000m", "memory": "1Gi"},
        }

    def scaffold_files(self) -> list[tuple[str, str]]:
        """Generate full production-ready FastAPI application scaffolding."""
        project = self.ctx.project_name
        has_db = "postgres" in self.ctx.all_env_vars.get("DATABASE_URL", "")
        has_cache = "dragonfly" in self.ctx.all_env_vars.get("CACHE_URL", "") or "redis" in self.ctx.all_env_vars.get("REDIS_URL", "")

        files: list[tuple[str, str]] = []

        # 1. app/main.py
        # Dynamically build imports and router registrations from WiringInfo
        nikame_imports = [
            "from routers import health",
            "from core.database import engine as db_engine",
        ]
        nikame_routers = []

        if has_cache:
            nikame_imports.append("from core.cache import redis_client")

        # Add hardcoded internal features first (or transition them to wiring too)
        # For now, we still have auth/storage/profiles as hardcoded feature routers
        feature_routers = {
            "auth": ("auth.router", "auth_router", "/auth", ["auth"]),
            "file_upload": ("storage.router", "storage_router", "/storage", ["storage"]),
            "profiles": ("profiles.router", "profiles_router", "/profiles", ["profiles"]),
        }

        for feature in self.ctx.features:
            if feature in feature_routers:
                mod, alias, prefix, tags = feature_routers[feature]
                nikame_imports.append(f"from {mod} import router as {alias}")
                nikame_routers.append(f"app.include_router({alias}, prefix=\"{prefix}\", tags={tags})")

        # Now add truly dynamic wiring from advanced components
        for feat_name, wiring in self.ctx.wiring.items():
            if feat_name in feature_routers:
                continue # Already handled (for now)
            
            for imp in wiring.imports:
                nikame_imports.append(imp)
            for router in wiring.routers:
                nikame_routers.append(router)

        imports_block = "\n".join(nikame_imports)
        routers_block = "\n".join(nikame_routers)

        main_py = f'''"""
FastAPI application entry point.
Auto-generated by NIKAME for project: {project}
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
{imports_block}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic: verify connections
    print(f"Starting {{settings.APP_NAME}} in {{settings.APP_ENV}} mode")
    try:
        # Test DB connection
        async with db_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✓ Database connection verified")
    except Exception as e:
        print(f"⚠ Database connection failed: {{e}}")
    
    yield
    # Shutdown logic
    await db_engine.dispose()
    print(f"Shutting down {{settings.APP_NAME}}")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router)

# Import text for startup check
from sqlalchemy import text
{routers_block}

@app.get("/")
async def root():
    return {{"message": f"Welcome to {{settings.APP_NAME}}", "env": settings.APP_ENV}}
'''
        files.append(("app/main.py", main_py))

        # Ensure feature folders have __init__.py if they are being registered
        for feature in self.ctx.features:
            if feature == "auth":
                files.append(("app/auth/__init__.py", ""))
            elif feature == "file_upload":
                files.append(("app/storage/__init__.py", ""))
            elif feature == "profiles":
                files.append(("app/profiles/__init__.py", ""))

        # 2. services/api/config.py
        config_py = f'''"""
Application configuration using Pydantic Settings.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "{project}"
    APP_ENV: str = "local"
    CORS_ORIGINS: List[str] = ["*"]

    # Database
    DATABASE_URL: str = "{self.ctx.all_env_vars.get('DATABASE_URL', '')}"

    # Cache
    CACHE_URL: str = "{self.ctx.all_env_vars.get('CACHE_URL', self.ctx.all_env_vars.get('REDIS_URL', ''))}"

{"".join([f"    {field}\n" for wiring in self.ctx.wiring.values() for field in wiring.settings_fields])}
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
'''
        files.append(("app/config.py", config_py))

        # 3. app/routers/health.py
        health_py = '''"""
Health and readiness probes.
"""

from fastapi import APIRouter, HTTPException
from config import settings
import httpx

router = APIRouter(prefix="/health", tags=["monitoring"])

from core.database import engine as db_engine

@router.get("/")
async def health_check():
    """Liveness probe."""
    return {"status": "healthy"}

@router.get("/ready")
async def readiness_check():
    """Readiness probe — checks dependencies."""
    from sqlalchemy import text
    checks = {"api": "ok"}
    
    # 1. Database Check
    try:
        async with db_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "fail"

    # 2. Cache Check
    try:
        from core.cache import redis_client
        await redis_client.ping()
        checks["cache"] = "ok"
    except Exception:
        # Only fail if cache is actually required/configured
        # For now we just report it
        checks["cache"] = "fail"
    
    if "fail" in checks.values():
        raise HTTPException(status_code=503, detail=f"Service unavailable: {checks}")
    
    return {"status": "ready", "components": checks}
'''
        files.append(("app/routers/__init__.py", ""))
        files.append(("app/routers/health.py", health_py))

        # 4. app/core/database.py
        if has_db:
            db_session = '''"""
SQLAlchemy async session management.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://"),
    echo=settings.APP_ENV == "local",
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
'''
            files.append(("app/core/__init__.py", ""))
            files.append(("app/core/database.py", db_session))

        # 5. app/core/cache.py
        if has_cache:
            cache_py = f'''"""
Redis/Dragonfly client configuration.
"""

import redis.asyncio as redis
from config import settings

redis_client = redis.from_url(
    settings.CACHE_URL,
    encoding="utf-8",
    decode_responses=True,
    socket_timeout=5,
)

async def get_cache():
    return redis_client
'''
            if ("app/core/__init__.py", "") not in files:
                files.append(("app/core/__init__.py", ""))
            files.append(("app/core/cache.py", cache_py))

        # 5. app/Dockerfile
        dockerfile = f'''# Multi-stage production-ready Dockerfile for FastAPI
# Generated by NIKAME

FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

# Run as non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE {self.port}

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{self.port}", "--proxy-headers"]
'''
        files.append(("app/Dockerfile", dockerfile))

        # 6. app/requirements.txt
        reqs = [
            "fastapi>=0.109.0",
            "uvicorn[standard]>=0.27.0",
            "pydantic-settings>=2.1.0",
            "httpx>=0.26.0",
        ]
        if has_db:
            reqs.extend(["sqlalchemy>=2.0.0", "asyncpg>=0.29.0"])
        if has_cache:
            reqs.append("redis>=5.0.0")

        files.append(("app/requirements.txt", "\n".join(reqs) + "\n"))

        # 7. Aggregate additional requirements from components
        for wiring in self.ctx.wiring.values():
            if wiring.requirements:
                reqs.extend(wiring.requirements)
        
        # Rewrite requirements with all dependencies
        files[-1] = ("app/requirements.txt", "\n".join(sorted(list(set(reqs)))) + "\n")

        # 8. app/.dockerignore
        dockerignore = """
__pycache__
*.pyc
.env
.venv
venv
.git
.gitignore
.dockerignore
"""
        files.append(("app/.dockerignore", dockerignore.strip() + "\n"))

        return files
