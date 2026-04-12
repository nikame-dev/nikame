# 🛸 NIKAME Generated Dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv     --mount=type=bind,source=pyproject.toml,target=pyproject.toml     uv sync --frozen --no-install-project --no-dev

# Builder stage for the project
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv     uv sync --frozen --no-dev

# Final runtime stage
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy the environment from the builder
COPY --from=builder /app/.venv /app/.venv
COPY . /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
