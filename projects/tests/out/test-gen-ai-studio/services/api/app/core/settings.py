"""Application settings — auto-wired by NIKAME."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All environment variables used across the application."""

    database_url: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    test_database_url: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
