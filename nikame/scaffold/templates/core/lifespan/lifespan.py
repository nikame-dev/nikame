"""
FastAPI Lifespan management.

Manages application startup and shutdown events asynchronously.
Useful for initializing DB pools, loading ML models, or managing
connections like Redis and external API clients.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Code before `yield` runs on app startup.
    Code after `yield` runs on app shutdown.
    """
    # ─── STARTUP ────────────────────────────────────
    # Example: Initialize database connection pool
    # app.state.db_pool = await create_db_pool()
    
    # Example: Load ML models into memory
    # app.state.model = await load_ml_model()
    
    # Example: Initialize shared httpx.AsyncClient
    # app.state.http_client = httpx.AsyncClient()
    
    yield  # Application serves requests while suspended here
    
    # ─── SHUTDOWN ───────────────────────────────────
    # Example: Close httpx client
    # if hasattr(app.state, "http_client"):
    #     await app.state.http_client.aclose()
    
    # Example: Close database pool
    # if hasattr(app.state, "db_pool"):
    #     await app.state.db_pool.close()
