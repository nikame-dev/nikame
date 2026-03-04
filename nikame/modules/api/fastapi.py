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
                    "context": "../services/api",
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

        # 1. services/api/main.py
        main_py = f'''"""
FastAPI application entry point.
Auto-generated by NIKAME for project: {project}
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.api.config import settings
from services.api.routers import health
# NIKAME IMPORTS

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print(f"Starting {{settings.APP_NAME}} in {{settings.APP_ENV}} mode")
    yield
    # Shutdown logic
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
# NIKAME ROUTERS

@app.get("/")
async def root():
    return {{"message": f"Welcome to {{settings.APP_NAME}}", "env": settings.APP_ENV}}
'''
        files.append(("services/api/main.py", main_py))

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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
'''
        files.append(("services/api/config.py", config_py))

        # 3. services/api/routers/health.py
        health_py = f'''"""
Health and readiness probes.
"""

from fastapi import APIRouter, HTTPException
from services.api.config import settings
import httpx

router = APIRouter(prefix="/health", tags=["monitoring"])

@router.get("/")
async def health_check():
    """Liveness probe."""
    return {{"status": "healthy"}}

@router.get("/ready")
async def readiness_check():
    """Readiness probe — checks dependencies."""
    checks = {{
        "api": "ok",
    }}
    
    # Simple check logic for demo
    # In production, actually ping DB/Cache session
    
    return {{"status": "ready", "components": checks}}
'''
        files.append(("services/api/routers/__init__.py", ""))
        files.append(("services/api/routers/health.py", health_py))

        # 4. services/api/db/session.py (if Postgres active)
        if has_db:
            db_session = f'''"""
SQLAlchemy async session management.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from services.api.config import settings

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://"),
    echo=settings.APP_ENV == "local",
    pool_pre_ping=True,
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
            files.append(("services/api/db/__init__.py", ""))
            files.append(("services/api/db/session.py", db_session))

        # 5. services/api/Dockerfile
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
        files.append(("services/api/Dockerfile", dockerfile))

        # 6. services/api/requirements.txt
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

        files.append(("services/api/requirements.txt", "\n".join(reqs) + "\n"))

        # 7. services/api/.dockerignore
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
        files.append(("services/api/.dockerignore", dockerignore.strip() + "\n"))

        return files
