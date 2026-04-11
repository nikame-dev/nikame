# Kubernetes Probes

Provides optimized YAML snippets for managing the lifecycle of AI-heavy FastAPI applications in Kubernetes.

## Why optimized probes?

Standard K8s probes often timeout if your model takes 30+ seconds to load into VRAM. By using a **Startup Probe**, we tell Kubernetes: "Don't restart me yet, I'm just loading." Once the Startup Probe succeeds, the regular Liveness and Readiness probes take over.

## Probes Explained

1.  **Startup Probe**: Only runs once at boot. Dedicated to heavy initialization.
2.  **Liveness Probe**: Runs continuously. If this fails, the container is restarted. Use for detecting Python event loop deadlocks.
3.  **Readiness Probe**: Runs continuously. If this fails, traffic is stopped but the container is *not* restarted. Use this for detecting transient failures like a database being briefly unreachable.

## Usage

Ensure you have implemented the `observability/health-checks` pattern first, then copy the snippets from `k8s/probes.yaml` into your Helm chart or K8s manifest.
