"""
Application configuration using Pydantic Settings.
"""

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App
    APP_NAME: str = "test-rag-scenario"
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
    DATABASE_URL: str = "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@pgbouncer:5432/${POSTGRES_DB}"

    # Cache
    CACHE_URL: str = ""

    # Messaging
    KAFKA_BOOTSTRAP_SERVERS: str = "redpanda:9092"
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    ELASTICSEARCH_URL: str = "http://elasticsearch:9200"
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    CLICKHOUSE_URL: str = "clickhouse://default:@clickhouse:9000/default"
    QDRANT_URL: str = "http://qdrant:6333"
    TEMPORAL_TARGET: str = "temporal:7233"
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "user"
    SMTP_PASSWORD: str = "password"
    NGROK_AUTHTOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
