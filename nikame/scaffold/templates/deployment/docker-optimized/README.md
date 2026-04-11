# Optimized Dockerfile

This pattern provides a production-hardened Docker configuration for your FastAPI application.

## Best Practices Included

1.  **Multi-Stage Build**: Separates the build environment from the runtime environment, resulting in significantly smaller image sizes (up to 70% reduction).
2.  **Non-Root User**: Runs the application as `appuser` instead of `root`. This is a critical security requirement for SOC2 and production environments.
3.  **Layer Caching**: Copies `requirements.txt` first. If your code changes but your dependencies don't, Docker will skip the expensive `pip install` step.
4.  **Signal Handling**: Python in Docker often ignores `SIGTERM`. We recommend using an init process like `tini` or `dumb-init` for graceful shutdowns.
5.  **Small Base Image**: Uses `python:3.11-slim` instead of the full images.

## Usage

Simply run:
```bash
docker build -t my-fastapi-app .
docker run -p 8000:8000 my-fastapi-app
```

## Gotchas

-   **GPU Support**: If you are deploying AI models, this `slim` image won't work. You must use `nvidia/cuda` as a base image and install Python on top of it.
-   **Architecture**: Ensure you build for the correct target architecture (e.g., `--platform linux/amd64` for most cloud provider deployments).
-   **Static Files**: FastAPI is not an optimized web server for large static files. Consider using Nginx or a CDN for production static asset delivery.
