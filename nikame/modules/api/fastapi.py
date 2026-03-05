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
        has_db = any(m.NAME in ["postgres", "timescaledb", "cockroachdb"] for m in self.ctx.blueprint.modules)
        has_cache = "dragonfly" in [m.NAME for m in self.ctx.blueprint.modules] or "redis" in [m.NAME for m in self.ctx.blueprint.modules]
        has_messaging = "redpanda" in [m.NAME for m in self.ctx.blueprint.modules] or "kafka" in [m.NAME for m in self.ctx.blueprint.modules]

        files: list[tuple[str, str]] = []

        # 1. app/main.py
        nikame_imports = [
            "from routers import health",
            "from sqlalchemy import text",
        ]
        
        if has_db:
            nikame_imports.append("from core.database import engine as db_engine")
        if has_cache:
            nikame_imports.append("from core.cache import cache")
        if has_messaging:
            nikame_imports.append("from core.messaging import kafka_service")

        imports_block = "\n".join(sorted(set(nikame_imports)))

        main_py = f'''"""
FastAPI application entry point.
Auto-generated by NIKAME for project: {project}
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import settings
import time
import logging

{imports_block}

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info(f"🚀 Starting {{settings.APP_NAME}} [{{settings.APP_ENV}}]")
    
    # 1. Database connection check
    if {has_db}:
        try:
            async with db_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("✓ Database connection verified")
        except Exception as e:
            logger.error(f"✗ Database connection failed: {{e}}")
    
    # 2. Redis/Dragonfly connection check
    if {has_cache}:
        try:
            await cache.connect()
            logger.info("✓ Cache connection verified")
        except Exception as e:
            logger.error(f"✗ Cache connection failed: {{e}}")

    # 3. Kafka/RedPanda connection check
    if {has_messaging}:
        try:
            await kafka_service.start()
            logger.info("✓ Messaging service (Kafka) started")
        except Exception as e:
            logger.error(f"✗ Messaging service failed: {{e}}")

    yield
    
    # Shutdown logic
    if {has_db}:
        await db_engine.dispose()
    if {has_cache}:
        await cache.disconnect()
    if {has_messaging}:
        await kafka_service.stop()
        
    logger.info(f"💤 Shutting down {{settings.APP_NAME}}")

app = FastAPI(
    title=settings.APP_NAME,
    description="Full-stack API generated by NIKAME",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {{exc}}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={{"detail": "Internal Server Error", "type": type(exc).__name__}},
    )

# Routes
app.include_router(health.router)

@app.get("/", tags=["root"])
async def root():
    return {{
        "message": f"Welcome to {{settings.APP_NAME}}",
        "env": settings.APP_ENV,
        "docs": "/docs",
        "health": "/health"
    }}
'''
        files.append(("app/main.py", main_py))

        # 2. app/config.py
        config_py = f'''"""
Application configuration using Pydantic Settings.
"""

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App
    APP_NAME: str = "{project}"
    APP_ENV: str = "local"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    DATABASE_URL: str = "{self.ctx.all_env_vars.get('DATABASE_URL', '')}"

    # Cache
    CACHE_URL: str = "{self.ctx.all_env_vars.get('CACHE_URL', self.ctx.all_env_vars.get('REDIS_URL', ''))}"

    # Messaging
    KAFKA_BOOTSTRAP_SERVERS: str = "{self.ctx.all_env_vars.get('KAFKA_BOOTSTRAP_SERVERS', 'redpanda:9092')}"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
'''
        files.append(("app/config.py", config_py))

        # 3. app/core/database.py
        if has_db:
            db_session = '''"""
SQLAlchemy async session management.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://"),
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
            files.append(("app/core/database.py", db_session))

        # 4. app/core/cache.py
        if has_cache:
            cache_py = '''"""
Cache client wrapper (Redis/Dragonfly).
"""

import redis.asyncio as redis
from config import settings
import logging

logger = logging.getLogger(__name__)

class CacheClient:
    def __init__(self, url: str):
        self._url = url
        self._client = None

    async def connect(self):
        if not self._client:
            self._client = redis.from_url(
                self._url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
            )
        await self._client.ping()

    async def disconnect(self):
        if self._client:
            await self._client.close()

    async def get(self, key: str):
        return await self._client.get(key)

    async def set(self, key: str, value: str, expire: int = None):
        return await self._client.set(key, value, ex=expire)

    async def delete(self, key: str):
        return await self._client.delete(key)
    
    async def ping(self):
        return await self._client.ping()

cache = CacheClient(settings.CACHE_URL)
'''
            files.append(("app/core/cache.py", cache_py))

        # 5. app/core/messaging.py
        if has_messaging:
            messaging_py = '''"""
Kafka/RedPanda messaging service.
"""

import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from config import settings
import json

logger = logging.getLogger(__name__)

class MessagingService:
    def __init__(self, bootstrap_servers: str):
        self._bootstrap_servers = bootstrap_servers
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    async def start(self):
        await self._producer.start()

    async def stop(self):
        await self._producer.stop()

    async def send_message(self, topic: str, message: dict):
        logger.info(f"Sending message to topic {topic}: {message}")
        await self._producer.send_and_wait(topic, message)

kafka_service = MessagingService(settings.KAFKA_BOOTSTRAP_SERVERS)
'''
            files.append(("app/core/messaging.py", messaging_py))

        # 6. app/routers/health.py
        health_py = f'''"""
Deep health checks for all system components.
"""

from fastapi import APIRouter, HTTPException
from config import settings
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["monitoring"])

@router.get("/")
async def liveness():
    """Basic liveness probe."""
    return {{"status": "ok", "service": settings.APP_NAME}}

@router.get("/ready")
async def readiness():
    """Deep readiness probe checking all sub-systems."""
    checks = {{}}
    
    # 1. Database
    if {has_db}:
        try:
            from core.database import engine
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "healthy"
        except Exception as e:
            logger.error(f"Health check: Database failed: {{e}}")
            checks["database"] = "unhealthy"

    # 2. Cache
    if {has_cache}:
        try:
            from core.cache import cache
            await cache.ping()
            checks["cache"] = "healthy"
        except Exception as e:
            logger.error(f"Health check: Cache failed: {{e}}")
            checks["cache"] = "unhealthy"

    if "unhealthy" in checks.values():
        raise HTTPException(status_code=503, detail=checks)
        
    return {{"status": "ready", "checks": checks}}
'''
        files.append(("app/routers/__init__.py", ""))
        files.append(("app/routers/health.py", health_py))

        # 7. app/Dockerfile
        dockerfile = f'''# Multi-stage production-ready Dockerfile for FastAPI
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
RUN useradd -m appuser && chown -R appuser /app
USER appuser
EXPOSE {self.port}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{self.port}", "--proxy-headers", "--forwarded-allow-ips", "*"]
'''
        files.append(("app/Dockerfile", dockerfile))

        # 8. app/requirements.txt
        reqs = [
            "fastapi>=0.109.0",
            "uvicorn[standard]>=0.27.0",
            "pydantic-settings>=2.1.0",
            "httpx>=0.26.0",
            "python-logging-loki>=0.3.1",
        ]
        if has_db:
            reqs.extend(["sqlalchemy>=2.0.0", "asyncpg>=0.29.0"])
        if has_cache:
            reqs.append("redis>=5.0.0")
        if has_messaging:
            reqs.append("aiokafka>=0.10.0")

        files.append(("app/requirements.txt", "\n".join(sorted(set(reqs))) + "\n"))
        files.append(("app/.dockerignore", "__pycache__\n*.pyc\n.env\n.venv\n.git\n"))

        return files

