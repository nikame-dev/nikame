FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for postgres build
RUN apt-get update && apt-get install -y libpq-dev gcc curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a local nikame repo directory within the container
# to install the local nikame package (this simulates testing).
# Alternatively, if nikame is published, it could be pip installed.
# But for now, we just ensure FastAPI works.
RUN pip uninstall -y nikame || true

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
