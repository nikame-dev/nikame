from typing import Literal

from pydantic import BaseModel, field_validator


class CopilotConfig(BaseModel):
    provider: Literal["ollama", "openai", "anthropic", "groq"] = "ollama"
    model: str = "qwen2.5-coder:7b"
    temperature: float = 0.2
    max_context_tokens: int = 8192

class EnvironmentConfig(BaseModel):
    target: Literal["local", "aws", "gcp", "azure"] = "local"
    resource_tier: Literal["small", "medium", "large"] = "medium"
    domain: str | None = None

class ObservabilityConfig(BaseModel):
    metrics: bool = False
    tracing: bool = False
    logging: Literal["stdout", "loki", "cloudwatch"] = "stdout"

class NikameConfig(BaseModel):
    version: Literal["2.0"] = "2.0"
    name: str
    description: str | None = None
    modules: list[str] = []        # dotted: "database.postgres", "auth.jwt"
    features: list[str] = []       # flat: "rate_limiting", "cron_jobs"
    environment: EnvironmentConfig = EnvironmentConfig()
    copilot: CopilotConfig = CopilotConfig()
    observability: ObservabilityConfig = ObservabilityConfig()

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, v: list[str]) -> list[str]:
        for mod in v:
            if "." not in mod:
                raise ValueError(f"Module '{mod}' must be dotted: e.g. 'database.postgres'")
        return v
