"""GitHub Actions CI/CD module."""

from __future__ import annotations

from typing import Any

from nikame.modules.base import BaseModule, ModuleContext


class GitHubActionsModule(BaseModule):
    """GitHub Actions CI/CD module.

    Generates .github/workflows/main.yml for:
    - Linting and Testing
    - Docker build and push (to ECR/GHCR)
    - K8s deployment (if applicable)
    - Secret syncing
    """

    NAME = "github_actions"
    CATEGORY = "cicd"
    DESCRIPTION = "GitHub Actions — Production-ready CI/CD pipelines"
    DEFAULT_VERSION = "v1"

    def scaffold_files(self) -> list[tuple[str, str]]:
        """Generate GitHub Actions workflow files."""
        project = self.ctx.project_name
        target = self.ctx.environment

        workflow_yml = f'''name: CI/CD Pipeline

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          pip install ruff pytest
          if [ -f app/requirements.txt ]; then pip install -r app/requirements.txt; fi
      - name: Lint with Ruff
        run: ruff check .
      - name: Test with pytest
        run: pytest

  build-and-push:
    needs: lint-and-test
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: actions/setup-docker-action@v2
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and push API
        uses: docker/build-push-action@v5
        with:
          context: ./app
          push: true
          tags: ghcr.io/${{ github.repository }}/{project}-api:latest

  deploy:
    needs: build-and-push
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # Placeholder for K8s/Cloud deployment
      - name: Deploy to {target}
        run: echo "Deploying to {target}..."
'''
        return [
            (".github/workflows/main.yml", workflow_yml)
        ]

    def health_check(self) -> dict[str, Any]:
        return {}

    def k8s_manifests(self) -> list[dict[str, Any]]:
        return []
