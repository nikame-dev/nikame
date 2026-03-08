"""Shared fixtures for generation correctness tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def minimal_buffer() -> dict[str, str]:
    """A minimal generated file buffer with one service."""
    return {
        "services/api/app/main.py": '''"""Main application."""
import os
from fastapi import FastAPI

app = FastAPI(title=os.getenv("SERVICE_NAME", "test-app"))

@app.get("/")
def root():
    return {"status": "ok"}
''',
        "services/api/requirements.txt": """fastapi>=0.109.0
uvicorn>=0.27.0
""",
        ".env.example": "SERVICE_NAME=test-app\n",
        ".env.generated": "SERVICE_NAME=test-app\n",
    }


@pytest.fixture
def full_stack_buffer() -> dict[str, str]:
    """A realistic generated buffer with multiple services, routers, middleware."""
    return {
        "services/api/app/main.py": '''"""Main FastAPI application."""
import os
from fastapi import FastAPI

app = FastAPI(title=os.getenv("SERVICE_NAME", "my-app"))

@app.get("/")
def root():
    return {"status": "ok"}
''',
        "services/api/app/routers/users.py": '''from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
async def list_users():
    return []
''',
        "services/api/app/routers/payments.py": '''from fastapi import APIRouter

router = APIRouter(prefix="/payments", tags=["billing"])

@router.post("/charge")
async def charge():
    return {"status": "charged"}
''',
        "services/api/app/core/integrations/database.py": '''"""PostgreSQL database integration."""
import os
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL")

async def startup():
    global engine
    engine = create_async_engine(DATABASE_URL, pool_size=25)

async def shutdown():
    pass

async def health_check():
    return {"status": "ok"}
''',
        "services/api/app/core/integrations/cache.py": '''"""Redis cache integration."""
import os
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL")

async def startup():
    global redis_client
    redis_client = redis.from_url(REDIS_URL)

async def shutdown():
    if redis_client:
        await redis_client.close()

async def health_check():
    return {"status": "ok"}
''',
        "services/api/app/middleware/tracing.py": '''"""Tracing middleware."""
import time

class TracingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)
''',
        "services/api/requirements.txt": """fastapi>=0.109.0
uvicorn>=0.27.0
sqlalchemy>=2.0.25
redis>=5.0.1
""",
        ".env.example": "SERVICE_NAME=my-app\n",
        ".env.generated": "SERVICE_NAME=my-app\n",
        "infra/docker-compose.yml": """services:
  api:
    build:
      context: ../services/api
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
""",
        "services/api/Dockerfile": """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
    }
