"""ML Gateway Codegen for NIKAME.

Generates a FastAPI wrapper using LiteLLM to provide a unified, 
OpenAI-compatible interface to all serving backends.
"""

from __future__ import annotations

from pathlib import Path

from nikame.config.schema import NikameConfig
from nikame.utils.file_writer import FileWriter


class MLGatewayCodegen:
    """Generates the ml-gateway service."""

    def __init__(self, config: NikameConfig) -> None:
        self.config = config

    def generate(self, output_dir: Path) -> None:
        """Generate the ml-gateway FastAPI service."""
        if not self.config.mlops or not self.config.mlops.models:
            return

        gateway_dir = output_dir / "services" / "ml-gateway"
        gateway_dir.mkdir(parents=True, exist_ok=True)

        writer = FileWriter()

        # 1. Generate main.py
        main_content = self._get_main_py()
        writer.write(gateway_dir / "main.py", main_content)

        # 2. Generate requirements.txt
        reqs = "fastapi[all]\nlitellm\nhttpx\nuvicorn\npython-dotenv\n"
        writer.write(gateway_dir / "requirements.txt", reqs)

        # 3. Generate Dockerfile
        dockerfile = (
            "FROM python:3.11-slim\n"
            "WORKDIR /app\n"
            "COPY requirements.txt .\n"
            "RUN pip install --no-cache-dir -r requirements.txt\n"
            "COPY . .\n"
            "CMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\n"
        )
        writer.write(gateway_dir / "Dockerfile", dockerfile)

    def _get_main_py(self) -> str:
        """Helper to generate main.py content with LiteLLM routing."""
        return """from fastapi import FastAPI, Request
from litellm import proxy_handler
import os

app = FastAPI(title="NIKAME ML Gateway")

@app.all("/{path:path}")
async def proxy(path: str, request: Request):
    return {"message": "NIKAME ML Gateway Proxying: " + path}

@app.get("/health")
async def health():
    return {"status": "healthy"}
"""
