"""Application settings — auto-wired by NIKAME."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All environment variables used across the application."""

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    database_url: str = ""
    evidently_host: str = ""
    mlflow_s3_endpoint_url: str = ""
    test_database_url: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
