"""
Application settings via Pydantic.

Loads from .env file or environment variables.
Provides type coercion and validation for all configuration.
"""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.
    
    Environment variables overriding these fields take precedence.
    """
    # Base
    APP_ENV: Literal["development", "production", "test"] = "development"
    DEBUG: bool = False
    
    # Secrets
    SECRET_KEY: str = "change_me_in_prod"
    
    # Database
    DB_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/dbname"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Hugging Face
    HF_TOKEN: str | None = None
    HF_HOME: str = "~/.cache/huggingface"
    HF_MODEL_NAME: str = "mistralai/Mistral-7B-Instruct-v0.2"
    
    # Model loading
    MODEL_DEVICE: Literal["auto", "cuda", "cpu", "mps"] = "auto"
    MODEL_DTYPE: Literal["auto", "float16", "bfloat16", "float32"] = "auto"
    MODEL_LOAD_IN_8BIT: bool = False
    MODEL_LOAD_IN_4BIT: bool = False
    MODEL_MAX_MEMORY: dict[str, str] | None = None  # e.g. {"0": "20GB"}
    
    # Local models
    MODELS_DIR: str = "~/.fastcheat/models"
    GGUF_MODEL_FILE: str = "mistral-7b.Q4_K_M.gguf"
    GGUF_N_GPU_LAYERS: int = -1
    GGUF_N_CTX: int = 4096
    
    # External model servers
    TGI_BASE_URL: str = "http://localhost:8080"
    VLLM_BASE_URL: str = "http://localhost:8000"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # Inference
    LLM_PROVIDER: str = "openai"  # openai, anthropic, ollama, vllm, gguf, hf-pipeline
    MAX_CONCURRENT_INFERENCE: int = 4
    INFERENCE_TIMEOUT_SECONDS: int = 30
    MODEL_WARMUP_RUNS: int = 2

    # Pydantic Settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Singleton instance
settings = Settings()
