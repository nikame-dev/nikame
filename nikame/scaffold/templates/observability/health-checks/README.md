# Health Checks

Standardized endpoints for monitoring application health, essential for Kubernetes, Docker Swarm, and AWS/GCP Load Balancers.

## Why differentiated probes?

1.  **Liveness (`/health/liveness`)**: Tells the orchestrator "I am not crashed." If this fails, K8s kills and restarts the container. Keep this extremely lightweight.
2.  **Readiness (`/health/readiness`)**: Tells the load balancer "I am ready to handle real users." This should fail if the Database is down or the 10GB Model is still loading.

## Usage

Mount the router:
```python
from app.routers.health import router as health_router
app.include_router(health_router)
```

## Kubernetes Example

```yaml
livenessProbe:
  httpGet:
    path: /health/liveness
    port: 8000
readinessProbe:
  httpGet:
    path: /health/readiness
    port: 8000
```
