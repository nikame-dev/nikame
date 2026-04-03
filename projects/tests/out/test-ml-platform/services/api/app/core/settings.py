"""Application settings — auto-wired by NIKAME."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All environment variables used across the application."""

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    database_url: str = ""
    evidently_host: str = ""
    langfuse_host: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    mlflow_s3_endpoint_url: str = ""
    test_database_url: str = ""
    test_redis_url: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
