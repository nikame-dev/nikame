# ---------------------------------------------------------
# Stage 1: Build dependencies
# ---------------------------------------------------------
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies if needed (e.g. gcc, libpq-dev)
# RUN apt-get update && apt-get install -y gcc libpq-dev

# Copy only requirements to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ---------------------------------------------------------
# Stage 2: Final Runtime
# ---------------------------------------------------------
FROM python:3.11-slim

# Security: Don't run as root
RUN useradd -m appuser
USER appuser
WORKDIR /home/appuser/app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY . .

# Environment Defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

# Use tini as init process if available for better signal handling
# ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
