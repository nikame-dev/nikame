import yaml
from typing import Any

from nikame.core.config.schema import NikameConfig
from nikame.core.manifest.schema import ManifestV2


class DockerfileGenerator:
    def generate(self, config: NikameConfig) -> str:
        """Generates a multi-stage Dockerfile optimized for Python/uv."""
        return f"""# 🛸 NIKAME Generated Dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Builder stage for the project
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Final runtime stage
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy the environment from the builder
COPY --from=builder /app/.venv /app/.venv
COPY . /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

class ComposeGenerator:
    def generate(self, config: NikameConfig, manifest: ManifestV2) -> str:
        """Generates a production-ready docker-compose.yml based on current manifest."""
        compose: dict[str, Any] = {
            "version": "3.8",
            "services": {
                "api": {
                    "build": ".",
                    "env_file": [".env"],
                    "ports": ["8000:8000"],
                    "depends_on": []
                }
            }
        }
        
        # Track allocated ports from manifest
        port_map = {p.service: p.port for p in manifest.ports_allocated}
        
        # Add basic services based on manifest patterns
        for pattern in manifest.patterns_applied:
            if pattern.id == "database.postgres":
                db_port = port_map.get("postgres", 5432)
                compose["services"]["postgres"] = {
                    "image": "postgres:15-alpine",
                    "environment": {
                        "POSTGRES_USER": "${POSTGRES_USER:-postgres}",
                        "POSTGRES_PASSWORD": "${POSTGRES_PASSWORD:-password}",
                        "POSTGRES_DB": "${POSTGRES_DB:-app_db}"
                    },
                    "ports": [f"{db_port}:5432"],
                    "volumes": ["postgres_data:/var/lib/postgresql/data"]
                }
                compose["services"]["api"]["depends_on"].append("postgres")
            elif pattern.id == "cache.redis":
                redis_port = port_map.get("redis", 6379)
                compose["services"]["redis"] = {
                    "image": "redis:7-alpine",
                    "ports": [f"{redis_port}:6379"]
                }
                compose["services"]["api"]["depends_on"].append("redis")
        
        if "volumes" not in compose and any(s.get("volumes") for s in compose["services"].values()):
             compose["volumes"] = {"postgres_data": {}}
                
        return "# 🛸 NIKAME Generated Docker Compose\n" + str(yaml.dump(compose, sort_keys=False))
