"""Pydantic v2 schema for nikame.yaml.

This is the single source of truth for all configuration shapes.
Every top-level key in nikame.yaml maps to a Pydantic model here.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

# ──────────────────────────── Environment ────────────────────────────


class EnvironmentConfig(BaseModel):
    """Deployment target and profile configuration."""

    target: Literal["local", "kubernetes", "aws", "gcp", "azure", "baremetal"] = "local"
    profile: Literal["local", "dev", "staging", "production"] = "local"
    cloud: Literal["aws", "gcp", "azure"] | None = None
    region: str | None = None
    namespace: str = "default"
    domain: str | None = None


# ──────────────────────────── API ────────────────────────────


class RateLimitingConfig(BaseModel):
    """Rate limiting configuration."""

    enabled: bool = False
    provider: str = "redis"
    requests_per_minute: int = 100


class APIAuthConfig(BaseModel):
    """API authentication configuration."""

    enabled: bool = False
    provider: str = "keycloak"


class TracingConfig(BaseModel):
    """Distributed tracing configuration."""

    enabled: bool = False
    provider: str = "otel"


class APIConfig(BaseModel):
    """API framework configuration."""

    framework: Literal["fastapi", "django", "flask"] = "fastapi"
    workers: int | Literal["auto"] = "auto"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    rate_limiting: RateLimitingConfig = Field(default_factory=RateLimitingConfig)
    auth: APIAuthConfig = Field(default_factory=APIAuthConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)


# ──────────────────────────── Databases ────────────────────────────


class PostgresConfig(BaseModel):
    """PostgreSQL database configuration."""

    version: str = "16"
    replicas: int = 1
    pgbouncer: bool = True
    extensions: list[str] = Field(default_factory=list)
    max_connections: int = 200
    storage: str = "10Gi"


class RedisConfig(BaseModel):
    """Redis / Valkey configuration."""

    version: str = "7"
    maxmemory: str = "256mb"
    persistence: bool = True
    cluster: bool = False


class DatabasesConfig(BaseModel):
    """All database configurations."""

    postgres: PostgresConfig | None = None
    redis: RedisConfig | None = None
    mongodb: dict[str, Any] | None = None
    clickhouse: dict[str, Any] | None = None
    qdrant: dict[str, Any] | None = None
    timescaledb: dict[str, Any] | None = None
    elasticsearch: dict[str, Any] | None = None
    neo4j: dict[str, Any] | None = None


# ──────────────────────────── Messaging ────────────────────────────


class TopicConfig(BaseModel):
    """Messaging topic configuration."""

    name: str
    partitions: int = 3
    retention_ms: int = 604800000  # 7 days


class RedPandaConfig(BaseModel):
    """RedPanda streaming configuration."""

    brokers: int = 1
    topics: list[TopicConfig] = Field(default_factory=list)
    schema_registry: bool = True
    kafka_ui: bool = True


class MessagingConfig(BaseModel):
    """Messaging system configuration."""

    redpanda: RedPandaConfig | None = None
    kafka: dict[str, Any] | None = None
    rabbitmq: dict[str, Any] | None = None
    nats: dict[str, Any] | None = None
    temporal: dict[str, Any] | None = None


# ──────────────────────────── Cache ────────────────────────────


class DragonflyConfig(BaseModel):
    """Dragonfly cache configuration."""

    maxmemory: str = "1gb"
    eviction_policy: str = "allkeys-lru"


class CacheConfig(BaseModel):
    """Cache layer configuration."""

    provider: Literal["dragonfly", "redis", "memcached"] = "dragonfly"
    dragonfly: DragonflyConfig = Field(default_factory=DragonflyConfig)


# ──────────────────────────── Storage ────────────────────────────


class StorageConfig(BaseModel):
    """Object storage configuration."""

    provider: Literal["minio", "seaweedfs", "s3"] = "minio"
    buckets: list[str] = Field(default_factory=lambda: ["uploads", "backups"])


# ──────────────────────────── Auth ────────────────────────────


class RealmConfig(BaseModel):
    """Keycloak realm configuration."""

    name: str = "main"
    social_providers: list[str] = Field(default_factory=list)
    mfa: Literal["disabled", "optional", "required"] = "optional"


class KeycloakConfig(BaseModel):
    """Keycloak-specific configuration."""

    realms: list[RealmConfig] = Field(default_factory=lambda: [RealmConfig()])


class PostgresAuthConfig(BaseModel):
    """PostgreSQL-specific authentication configuration."""

    jwt_secret: str = "super-secret-key"
    token_expiry: int = 3600


class AuthConfig(BaseModel):
    """Authentication provider configuration."""

    provider: Literal["keycloak", "authentik", "vault", "postgres", "jwt"] = "keycloak"
    keycloak: KeycloakConfig = Field(default_factory=KeycloakConfig)
    postgres: PostgresAuthConfig = Field(default_factory=PostgresAuthConfig)


# ──────────────────────────── Gateway ────────────────────────────


class TLSConfig(BaseModel):
    """TLS/SSL configuration."""

    enabled: bool = True
    provider: Literal["letsencrypt", "self-signed", "custom"] = "letsencrypt"
    email: str = ""


class GatewayConfig(BaseModel):
    """API gateway / reverse proxy configuration."""

    provider: Literal["traefik", "kong", "nginx", "caddy"] = "traefik"
    tls: TLSConfig = Field(default_factory=TLSConfig)


# ──────────────────────────── Observability ────────────────────────────


class AlertChannelConfig(BaseModel):
    """Alerting channel configuration."""

    type: Literal["slack", "email", "pagerduty", "webhook"] = "slack"
    webhook: str = ""


class AlertingConfig(BaseModel):
    """Alerting configuration."""

    channels: list[AlertChannelConfig] = Field(default_factory=list)


class ObservabilityConfig(BaseModel):
    """Monitoring and observability stack configuration."""

    stack: Literal["full", "lightweight", "none"] = "full"
    alerting: AlertingConfig = Field(default_factory=AlertingConfig)
    loki: bool = True
    tempo: bool = True
    otel_collector: bool = True
    uptime_kuma: bool = False


# ──────────────────────────── Security ────────────────────────────


class SecretsConfig(BaseModel):
    """Secrets management configuration."""

    provider: Literal["vault", "sealed-secrets", "env"] = "env"


class NetworkPolicyConfig(BaseModel):
    """Kubernetes network policy configuration."""

    provider: Literal["cilium", "calico", "none"] = "none"
    default_deny: bool = True


class SecurityConfig(BaseModel):
    """Security hardening configuration."""

    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    network_policy: NetworkPolicyConfig = Field(default_factory=NetworkPolicyConfig)
    tls: TLSConfig = Field(default_factory=TLSConfig)


# ──────────────────────────── CI/CD ────────────────────────────


class CICDConfig(BaseModel):
    """CI/CD system configuration."""

    gitea: bool = False
    woodpecker: bool = False
    argocd: bool = False
    github_actions: bool = True  # Default to True for architectural standard


# ──────────────────────────── Compute Optimization ────────────────────────────


class ComputeOptimizationConfig(BaseModel):
    """Compute and cost optimization configuration."""

    enabled: bool = True
    auto_suggest_alternatives: bool = True
    spot_instances: bool = False
    scale_to_zero: bool = False


# ──────────────────────────── MLOps ────────────────────────────


class ModelQuantizationConfig(BaseModel):
    """Model quantization configuration."""

    enabled: bool = True
    method: Literal["auto", "gguf", "awq", "gptq", "bitsandbytes"] = "auto"
    bits: int = 4


class MLModelConfig(BaseModel):
    """Configuration for a single ML model."""

    name: str
    source: Literal[
        "huggingface", "ollama", "custom", "openai_compatible", "onnx", "replicate"
    ] = "huggingface"
    model: str | None = None
    path: str | None = None
    revision: str = "main"
    token: str | None = None
    quantize: ModelQuantizationConfig = Field(default_factory=ModelQuantizationConfig)
    serve_with: Literal[
        "auto", "vllm", "ollama", "triton", "llamacpp", "bentoml", "tgi", "xinference", "localai", "whisper", "tts", "airllm"
    ] = "auto"
    replicas: int = 1
    gpu: Literal["required", "optional", "none"] = "optional"


class ServingConfig(BaseModel):
    provider: Literal["auto", "vllm", "ollama", "triton", "llamacpp", "bentoml", "tgi", "xinference", "localai", "whisper", "tts", "airllm"] = "auto"
    gpu: bool = False
    replicas: int = 1

class TrackingConfig(BaseModel):
    provider: Literal["mlflow", "dvc"] = "mlflow"
    endpoint: str | None = None

class OrchestrationConfig(BaseModel):
    provider: Literal["prefect", "airflow", "zenml", "temporal"] = "prefect"

class MLOpsConfig(BaseModel):
    """MLOps and model serving configuration."""

    models: list[MLModelConfig] = Field(default_factory=list)
    serving: ServingConfig | list[str] = Field(default_factory=ServingConfig)
    tracking: TrackingConfig | list[Literal["mlflow", "dvc"]] = Field(default_factory=TrackingConfig)
    feature_store: list[Literal["feast", "hopsworks"]] = Field(default_factory=list)
    orchestration: OrchestrationConfig | list[Literal["prefect", "airflow", "zenml", "temporal"]] = Field(
        default_factory=OrchestrationConfig
    )
    monitoring: list[Literal["evidently", "langfuse", "arize-phoenix"]] = Field(
        default_factory=list
    )
    vector_dbs: list[Literal["qdrant", "weaviate", "milvus", "chroma", "pgvector"]] = Field(
        default_factory=list
    )
    caching: list[Literal["gptcache"]] = Field(default_factory=list)
    agents: list[Literal["langchain", "llamaindex", "haystack"]] = Field(
        default_factory=list
    )
    training_enabled: bool = False
    embedding_dim: int | None = None
    orchestrator: str | None = None


# ──────────────────────────── Data Modeling ────────────────────────────


class FieldConfig(BaseModel):
    """Configuration for a single model field."""

    type: str = "str"
    required: bool = False
    indexed: bool = False
    unique: bool = False
    nullable: bool = True
    default: Any = None
    values: list[str] | None = None  # For enum types
    searchable: bool = False
    sortable: bool = True


class RelationshipConfig(BaseModel):
    """Configuration for model-to-model relationships."""

    type: Literal["one-to-many", "many-to-one", "many-to-many", "one-to-one"]
    model: str
    backref: str | None = None
    on_delete: Literal["CASCADE", "SET NULL", "RESTRICT"] = "SET NULL"


class DataModelConfig(BaseModel):
    """Configuration for a data entity."""

    fields: dict[str, FieldConfig | str] = Field(default_factory=dict)
    relationships: dict[str, RelationshipConfig] = Field(default_factory=dict)
    soft_delete: bool = False
    audit_log: bool = False
    admin_panel: bool = True


# ──────────────────────────── Project Metadata ────────────────────────────


class ProjectConfig(BaseModel):
    """Deep metadata for project automation."""

    scale: Literal["small", "medium", "large"] = "small"
    access_pattern: Literal["read_heavy", "write_heavy", "balanced"] = "balanced"
    raw_models: str | None = None


# ──────────────────────────── ROOT CONFIG ────────────────────────────


class NikameConfig(BaseModel):
    """Root configuration model for nikame.yaml.

    This is the single source of truth for an entire NIKAME project.
    Every field corresponds to a top-level key in the YAML config.
    """

    name: str
    version: str = "1.0"
    description: str = ""
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig)
    api: APIConfig | None = None
    databases: DatabasesConfig | None = None
    messaging: MessagingConfig | None = None
    cache: CacheConfig | None = None
    storage: StorageConfig | None = None
    auth: AuthConfig | None = None
    gateway: GatewayConfig | None = None
    observability: ObservabilityConfig | None = None
    security: SecurityConfig | None = None
    mlops: MLOpsConfig | None = None
    models: dict[str, DataModelConfig] = Field(default_factory=dict)
    ci_cd: CICDConfig = Field(default_factory=CICDConfig)
    ngrok: dict[str, Any] | None = None
    unleash: dict[str, Any] | None = None
    compute_optimization: ComputeOptimizationConfig = Field(
        default_factory=ComputeOptimizationConfig
    )
    features: list[str] = Field(default_factory=list)
    plugins: list[str] = Field(default_factory=list)
    generate_guide: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure project name is a valid identifier."""
        sanitized = v.strip().lower().replace(" ", "-")
        if not sanitized:
            msg = "Project name must not be empty"
            raise ValueError(msg)
        return sanitized
