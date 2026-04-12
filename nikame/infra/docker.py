from nikame.core.config.schema import NikameConfig
from nikame.core.manifest.schema import ManifestV2
import yaml

class DockerfileGenerator:
    def generate(self, config: NikameConfig) -> str:
        # Multi-stage Dockerfile using uv
        content = [
            "FROM python:3.11-slim as builder",
            "RUN pip install uv",
            "WORKDIR /app",
            "COPY pyproject.toml .",
            "RUN uv pip install -r pyproject.toml",
            "",
            "FROM python:3.11-slim as runtime",
            "RUN useradd -m -s /bin/bash appuser",
            "USER appuser",
            "WORKDIR /app",
            "COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages",
            "COPY . .",
            "HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/health || exit 1",
            "CMD [\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]"
        ]
        return "\n".join(content)

class ComposeGenerator:
    def generate(self, config: NikameConfig, manifest: ManifestV2) -> str:
        compose = {
            "version": "3.8",
            "services": {
                "api": {
                    "build": ".",
                    "ports": ["8000:8000"],
                    "environment": ["ENV=prod"],
                    "depends_on": []
                }
            }
        }
        
        # Add basic services based on config modules
        for mod in config.modules:
            if mod == "database.postgres":
                compose["services"]["postgres"] = { # type: ignore
                    "image": "postgres:15-alpine",
                    "environment": {
                        "POSTGRES_USER": "postgres",
                        "POSTGRES_PASSWORD": "password",
                        "POSTGRES_DB": "app_db"
                    },
                    "ports": ["5432:5432"]
                }
                compose["services"]["api"]["depends_on"].append("postgres") # type: ignore
            elif mod == "cache.redis":
                compose["services"]["redis"] = { # type: ignore
                    "image": "redis:7-alpine",
                    "ports": ["6379:6379"]
                }
                compose["services"]["api"]["depends_on"].append("redis") # type: ignore
                
        return yaml.dump(compose, sort_keys=False)
