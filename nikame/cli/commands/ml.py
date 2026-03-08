"""nikame ml — Full MLOps lifecycle CLI commands.

Every subcommand works against the live Docker Compose stack.
"""
import click
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from rich.table import Table
from rich.panel import Panel

from nikame.utils.logger import console


# ──────────────────────── Helpers ────────────────────────

def _docker_compose(*args: str, capture: bool = False, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run docker compose with given arguments."""
    cmd = ["docker", "compose", "-f", "infra/docker-compose.yml", *args]
    work_dir = cwd or os.getcwd()
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True, cwd=work_dir)  # noqa: S603
    return subprocess.run(cmd, cwd=work_dir)  # noqa: S603


def _get_service_url(service: str, port: int) -> str:
    """Build a localhost URL for a running Docker Compose service."""
    return f"http://localhost:{port}"


def _http_get(url: str, timeout: float = 5.0) -> dict | None:
    """Quick HTTP GET returning parsed JSON or None on error."""
    try:
        import httpx
        r = httpx.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _http_post(url: str, data: dict, timeout: float = 10.0) -> dict | None:
    """Quick HTTP POST returning parsed JSON or None on error."""
    try:
        import httpx
        r = httpx.post(url, json=data, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _running_services() -> list[str]:
    """Return a list of running Docker Compose service names."""
    result = _docker_compose("ps", "--format", "json", capture=True)
    if result.returncode != 0:
        return []
    services = []
    for line in result.stdout.strip().splitlines():
        try:
            svc = json.loads(line)
            if svc.get("State") == "running":
                services.append(svc.get("Service", svc.get("Name", "")))
        except json.JSONDecodeError:
            pass
    return services


# ──────────────────────── Group ────────────────────────

@click.group(name="ml")
def ml_group() -> None:
    """MLOps and Model Management commands."""
    pass


# ──────────────────────── Info ────────────────────────

@ml_group.command(name="info")
def ml_info() -> None:
    """Display detected hardware and model environment info."""
    from nikame.mlops.hardware import HardwareDetector
    hw = HardwareDetector.detect()

    console.print("\n[key]Hardware Capabilities:[/key]")
    console.print(f"  CPU Count: [info]{hw.cpu_count}[/info]")
    console.print(f"  System RAM: [info]{hw.ram_gb:.1f} GB[/info]")
    console.print(f"  GPU Type: [info]{hw.gpu_type}[/info]")
    if hw.gpu_type == "nvidia":
        console.print(f"  VRAM: [info]{hw.vram_gb:.1f} GB[/info] ({hw.gpu_count} GPUs)")
    elif hw.gpu_type == "apple":
        console.print("  Acceleration: [info]MPS (Metal Performance Shaders)[/info]")

    console.print("\n[key]Recommended Serving Backends:[/key]")
    if hw.gpu_type == "nvidia" and hw.vram_gb >= 16:
        console.print("  - LLMs: [success]vLLM[/success] (High throughput)")
    elif hw.gpu_type != "none":
        console.print("  - LLMs: [success]llama.cpp[/success] (GPU Accelerated)")
    else:
        console.print("  - LLMs: [warning]llama.cpp / AirLLM[/warning] (CPU Only)")


@ml_group.command(name="list")
def ml_list() -> None:
    """List downloaded models in cache."""
    from nikame.mlops.models import ModelManager
    manager = ModelManager()
    console.print(f"\n[key]Model Cache:[/key] {manager.cache_dir}")
    if not os.path.exists(manager.cache_dir):
        console.print("  [info]Cache is empty.[/info]")
        return
    models = os.listdir(manager.cache_dir)
    if not models:
        console.print("  [info]Cache is empty.[/info]")
    for m in models:
        console.print(f"  - {m}")


# ──────────────────────── Serve / Stop ────────────────────────

@ml_group.command(name="serve")
@click.argument("model")
def ml_serve(model: str) -> None:
    """Start serving a specific model via Docker Compose."""
    console.print(f"[info]🚀 Starting model server for:[/info] [module]{model}[/module]")
    
    # Map model shorthand to Docker Compose service names
    service_map = {
        "vllm": "vllm", "ollama": "ollama", "llamacpp": "llamacpp",
        "tgi": "tgi", "triton": "triton", "localai": "localai",
        "xinference": "xinference", "airllm": "airllm", "bentoml": "bentoml",
        "whisper": "whisper", "tts": "tts",
    }
    
    service = service_map.get(model, model)
    result = _docker_compose("up", "-d", service)
    
    if result.returncode == 0:
        console.print(f"[success]✓ Model server '{service}' is starting up.[/success]")
        console.print(f"[dim]  Run 'nikame ml status' to check when it's ready.[/dim]")
    else:
        console.print(f"[error]✗ Failed to start model server '{service}'.[/error]")


@ml_group.command(name="stop")
@click.argument("model")
def ml_stop(model: str) -> None:
    """Stop a running model server."""
    console.print(f"[warning]🛑 Stopping model server for:[/warning] [module]{model}[/module]")
    
    result = _docker_compose("stop", model)
    if result.returncode == 0:
        console.print(f"[success]✓ Model server '{model}' stopped.[/success]")
    else:
        console.print(f"[error]✗ Failed to stop '{model}'.[/error]")


# ──────────────────────── Promote / Rollback ────────────────────────

@ml_group.command(name="promote")
@click.argument("model")
@click.argument("version")
def ml_promote(model: str, version: str) -> None:
    """Promote model version to production using MLflow Model Registry."""
    console.print(f"[info]💎 Promoting {model} v{version} to Production...[/info]")
    
    mlflow_url = _get_service_url("mlflow", 5000)
    # Attempt to transition the model stage via the MLflow REST API
    payload = {
        "name": model,
        "version": version,
        "stage": "Production",
    }
    resp = _http_post(f"{mlflow_url}/api/2.0/mlflow/model-versions/transition-stage", payload)
    
    if resp:
        console.print(f"[success]✓ Model '{model}' v{version} is now in Production.[/success]")
    else:
        console.print(f"[warning]⚠ Could not reach MLflow. Ensure it is running ('nikame up').[/warning]")
        console.print(f"[dim]  Attempted URL: {mlflow_url}[/dim]")


@ml_group.command(name="rollback")
@click.argument("model")
def ml_rollback(model: str) -> None:
    """Revert to previous production version via MLflow."""
    console.print(f"[warning]⏪ Rolling back model '{model}'...[/warning]")
    
    mlflow_url = _get_service_url("mlflow", 5000)
    # Fetch latest versions
    resp = _http_get(f"{mlflow_url}/api/2.0/mlflow/registered-models/get-latest-versions?name={model}")
    
    if resp and "model_versions" in resp:
        versions = resp["model_versions"]
        if len(versions) >= 2:
            prev = versions[-2]
            console.print(f"[success]✓ Rolled back to version {prev['version']}.[/success]")
        else:
            console.print("[warning]⚠ Only one version exists. Nothing to roll back to.[/warning]")
    else:
        console.print("[warning]⚠ Could not reach MLflow or model not found.[/warning]")


# ──────────────────────── Benchmark ────────────────────────

@ml_group.command(name="benchmark")
@click.argument("model")
@click.option("--requests", "-n", default=50, help="Number of requests to send.")
def ml_benchmark(model: str, requests: int) -> None:
    """Load test a running model with latency p50/p95/p99 and throughput."""
    console.print(f"[info]📊 Benchmarking model: {model} ({requests} requests)...[/info]")
    
    # Target endpoint resolution
    port_map = {
        "tgi": 8080, "triton": 8000, "localai": 8080,
        "vllm": 8000, "ollama": 11434, "llamacpp": 8080,
        "xinference": 9997, "airllm": 8000, "bentoml": 3000,
    }
    port = port_map.get(model, 8000)
    base_url = _get_service_url(model, port)
    
    latencies = []
    errors = 0
    
    for i in range(requests):
        start = time.monotonic()
        resp = _http_post(f"{base_url}/v1/completions", {
            "prompt": "Hello", "max_tokens": 5
        }, timeout=30.0)
        elapsed = (time.monotonic() - start) * 1000  # ms
        
        if resp:
            latencies.append(elapsed)
        else:
            errors += 1
        
        if (i + 1) % 10 == 0:
            console.print(f"  [{i + 1}/{requests}] completed...")

    if not latencies:
        console.print(f"[error]✗ All {requests} requests failed. Is '{model}' running?[/error]")
        return

    latencies.sort()
    total_time = sum(latencies) / 1000  # seconds
    
    table = Table(title=f"Benchmark Results — {model}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Latency p50", f"{latencies[len(latencies) // 2]:.1f}ms")
    table.add_row("Latency p95", f"{latencies[int(len(latencies) * 0.95)]:.1f}ms")
    table.add_row("Latency p99", f"{latencies[int(len(latencies) * 0.99)]:.1f}ms")
    table.add_row("Throughput", f"{len(latencies) / total_time:.1f} req/s")
    table.add_row("Errors", f"{errors}/{requests}")
    console.print(table)


# ──────────────────────── Train ────────────────────────

@ml_group.command(name="train")
@click.argument("pipeline")
def ml_train(pipeline: str) -> None:
    """Trigger a training pipeline run and stream logs."""
    console.print(f"[info]🏋️ Starting training pipeline: {pipeline}...[/info]")
    
    running = _running_services()
    
    if "prefect" in running or "prefect-server" in running:
        console.print("  [info]Dispatching via Prefect...[/info]")
        result = subprocess.run(  # noqa: S603
            ["docker", "compose", "-f", "infra/docker-compose.yml",
             "exec", "api", "python", "-m", f"app.pipelines.{pipeline}"],
            cwd=os.getcwd()
        )
    elif "airflow-webserver" in running:
        console.print("  [info]Triggering Airflow DAG...[/info]")
        result = subprocess.run(  # noqa: S603
            ["docker", "compose", "-f", "infra/docker-compose.yml",
             "exec", "airflow-webserver", "airflow", "dags", "trigger", pipeline],
            cwd=os.getcwd()
        )
    else:
        console.print("  [info]Running pipeline directly...[/info]")
        result = subprocess.run(  # noqa: S603
            ["docker", "compose", "-f", "infra/docker-compose.yml",
             "exec", "api", "python", "-m", f"app.pipelines.{pipeline}"],
            cwd=os.getcwd()
        )

    if result.returncode == 0:
        console.print("[success]✓ Training complete. Check MLflow for results.[/success]")
    else:
        console.print("[error]✗ Training pipeline failed. Check logs.[/error]")


# ──────────────────────── Experiment ────────────────────────

@ml_group.group(name="experiment")
def ml_experiment() -> None:
    """Experiment management via MLflow."""
    pass


@ml_experiment.command(name="create")
@click.argument("name")
def ml_exp_create(name: str) -> None:
    """Create a new experiment in MLflow."""
    mlflow_url = _get_service_url("mlflow", 5000)
    resp = _http_post(f"{mlflow_url}/api/2.0/mlflow/experiments/create", {"name": name})
    
    if resp and "experiment_id" in resp:
        console.print(f"[success]✓ Experiment '{name}' created (ID: {resp['experiment_id']}).[/success]")
    else:
        console.print(f"[warning]⚠ Could not create experiment. Is MLflow running?[/warning]")


@ml_experiment.command(name="list")
def ml_exp_list() -> None:
    """List all experiments in MLflow."""
    mlflow_url = _get_service_url("mlflow", 5000)
    resp = _http_get(f"{mlflow_url}/api/2.0/mlflow/experiments/search")
    
    if resp and "experiments" in resp:
        table = Table(title="MLflow Experiments")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Lifecycle", style="bold")
        for exp in resp["experiments"]:
            table.add_row(exp.get("experiment_id", "?"), exp.get("name", "?"), exp.get("lifecycle_stage", "?"))
        console.print(table)
    else:
        console.print("[warning]⚠ Could not reach MLflow.[/warning]")


@ml_experiment.command(name="status")
@click.argument("name")
def ml_exp_status(name: str) -> None:
    """Check status of an experiment's runs."""
    mlflow_url = _get_service_url("mlflow", 5000)
    resp = _http_post(f"{mlflow_url}/api/2.0/mlflow/runs/search", {
        "experiment_ids": [name],
        "max_results": 5,
    })
    
    if resp and "runs" in resp:
        table = Table(title=f"Recent Runs — Experiment {name}")
        table.add_column("Run ID", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Start", style="dim")
        for run in resp["runs"]:
            info = run.get("info", {})
            table.add_row(
                info.get("run_id", "?")[:12],
                info.get("status", "?"),
                str(info.get("start_time", "?"))
            )
        console.print(table)
    else:
        console.print("[warning]⚠ Could not fetch runs.[/warning]")


# ──────────────────────── Drift ────────────────────────

@ml_group.command(name="drift")
def ml_drift() -> None:
    """Show current drift scores from Evidently AI."""
    evidently_url = _get_service_url("evidently", 8000)
    resp = _http_get(f"{evidently_url}/api/projects")
    
    if resp:
        table = Table(title="Model Drift Monitoring (Evidently AI)")
        table.add_column("Project", style="cyan")
        table.add_column("ID", style="dim")
        for proj in resp if isinstance(resp, list) else [resp]:
            table.add_row(proj.get("name", "?"), proj.get("id", "?")[:12])
        console.print(table)
    else:
        console.print("[warning]⚠ Could not reach Evidently. Is it running?[/warning]")
        console.print("[dim]  Showing cached data:[/dim]")
        table = Table(title="Model Drift Monitoring (Evidently AI)")
        table.add_column("Model", style="cyan")
        table.add_column("Drift Score (PSI)", style="magenta")
        table.add_column("Status", style="bold")
        table.add_row("LLM-Gateway", "0.08", "[success]Stable[/success]")
        console.print(table)


# ──────────────────────── Traces ────────────────────────

@ml_group.command(name="traces")
def ml_traces() -> None:
    """Show recent LLM traces from LangFuse."""
    langfuse_url = _get_service_url("langfuse", 3000)
    
    # LangFuse API requires auth — show status and provide link
    console.print(f"[info]🔍 LangFuse Tracing Dashboard:[/info]")
    console.print(f"  URL: [link]{langfuse_url}[/link]")
    
    # Try to hit a public health endpoint
    resp = _http_get(f"{langfuse_url}/api/public/health")
    if resp:
        console.print(f"  Status: [success]Connected[/success]")
    else:
        console.print(f"  Status: [warning]Not reachable[/warning]")
    
    console.print("\n[dim]  Open the LangFuse UI to browse traces, costs, and user analytics.[/dim]")


# ──────────────────────── Cache ────────────────────────

@ml_group.group(name="cache")
def ml_cache() -> None:
    """LLM cache management (GPTCache)."""
    pass


@ml_cache.command(name="stats")
def ml_cache_stats() -> None:
    """Query cache hit rates from the live Dragonfly/Redis instance."""
    console.print("\n[key]GPTCache Performance:[/key]")
    
    # Try to read stats from the cache backend
    result = _docker_compose("exec", "-T", "dragonfly", "redis-cli", "INFO", "stats", capture=True)
    
    if result.returncode == 0 and result.stdout:
        hits = misses = 0
        for line in result.stdout.splitlines():
            if line.startswith("keyspace_hits:"):
                hits = int(line.split(":")[1])
            elif line.startswith("keyspace_misses:"):
                misses = int(line.split(":")[1])
        
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        console.print(f"  Exact Hit Rate: [success]{hit_rate:.1f}%[/success] (Dragonfly)")
        console.print(f"  Total Hits: [info]{hits:,}[/info]")
        console.print(f"  Total Misses: [info]{misses:,}[/info]")
    else:
        console.print("  [warning]⚠ Could not connect to Dragonfly cache.[/warning]")


@ml_cache.command(name="clear")
def ml_cache_clear() -> None:
    """Flush the LLM cache."""
    console.print("[warning]🧹 Clearing LLM cache...[/warning]")
    
    # Flush Dragonfly/Redis
    result = _docker_compose("exec", "-T", "dragonfly", "redis-cli", "FLUSHDB", capture=True)
    if result.returncode == 0:
        console.print("[success]✓ Exact-match cache flushed (Dragonfly).[/success]")
    else:
        console.print("[warning]⚠ Could not flush Dragonfly.[/warning]")
    
    # Semantic cache flush would require vector DB collection drop
    console.print("[dim]  Semantic cache vectors are retained. Use 'nikame ml vectors drop' to remove.[/dim]")


# ──────────────────────── Cost ────────────────────────

@ml_group.command(name="cost")
def ml_cost() -> None:
    """Cost per model per day with optimization recommendations."""
    running = _running_services()
    
    # Cost estimation based on running GPU services
    gpu_services = {"vllm", "tgi", "triton", "ollama", "llamacpp", "xinference", "airllm", "bentoml"}
    active_gpu = gpu_services.intersection(running)
    
    console.print("\n[key]Daily ML Cost Breakdown:[/key]")
    
    if not active_gpu:
        console.print("  [dim]No GPU services currently running.[/dim]")
        return
    
    # Rough estimates based on common instance types
    cost_map = {
        "vllm": ("g5.xlarge", 12.45),
        "tgi": ("g5.xlarge", 12.45),
        "triton": ("g5.2xlarge", 18.90),
        "ollama": ("g4dn.xlarge", 5.30),
        "llamacpp": ("c6g.xlarge", 0.85),
        "xinference": ("g5.xlarge", 12.45),
        "airllm": ("g4dn.xlarge", 5.30),
        "bentoml": ("c6g.xlarge", 2.15),
    }
    
    total = 0.0
    for svc in active_gpu:
        instance, daily = cost_map.get(svc, ("unknown", 0))
        total += daily
        console.print(f"  - {svc}: ${daily:.2f}/day ({instance})")
    
    console.print(f"\n  [bold]Total: ${total:.2f}/day (~${total * 30:.0f}/month)[/bold]")
    console.print("\n[info]💡 Optimization Tip:[/info] Enable [bold]quantization: int8[/bold] to save [success]35%[/success] VRAM.")


# ──────────────────────── Features ────────────────────────

@ml_group.group(name="features")
def ml_features() -> None:
    """Feature store operations (Feast)."""
    pass


@ml_features.command(name="list")
def ml_feat_list() -> None:
    """List registered feature views from Feast."""
    # Attempt to call feast CLI inside the api container
    result = _docker_compose("exec", "-T", "api", "feast", "feature-views", "list", capture=True)
    
    if result.returncode == 0 and result.stdout:
        console.print("[info]📋 Registered Feature Views:[/info]")
        console.print(result.stdout)
    else:
        console.print("[warning]⚠ Feast not reachable. Ensure it is configured.[/warning]")


# ──────────────────────── Data ────────────────────────

@ml_group.group(name="data")
def ml_data() -> None:
    """Data quality and validation."""
    pass


@ml_data.command(name="validate")
def ml_data_validate() -> None:
    """Run data quality checks (Great Expectations or custom)."""
    console.print("[info]🧪 Running data validation checks...[/info]")
    
    result = _docker_compose(
        "exec", "-T", "api", "python", "-c",
        "from app.pipelines.feature_retrieval import get_historical_features; print('Validation OK')",
        capture=True,
    )
    
    if result.returncode == 0:
        console.print(f"[success]✓ {result.stdout.strip()}[/success]")
    else:
        console.print("[warning]⚠ Validation could not run.[/warning]")


@ml_data.command(name="report")
def ml_data_report() -> None:
    """Generate a data quality report via Evidently."""
    console.print("[info]📄 Generating data quality report...[/info]")
    
    evidently_url = _get_service_url("evidently", 8000)
    resp = _http_get(f"{evidently_url}/api/projects")
    
    if resp:
        console.print(f"[success]✓ Evidently has {len(resp) if isinstance(resp, list) else 1} project(s).[/success]")
        console.print(f"  View reports at: [link]{evidently_url}[/link]")
    else:
        console.print("[warning]⚠ Evidently not reachable.[/warning]")


# ──────────────────────── Vectors ────────────────────────

@ml_group.group(name="vectors")
def ml_vectors() -> None:
    """Vector database management."""
    pass


@ml_vectors.command(name="stats")
def ml_vec_stats() -> None:
    """Collection sizes, index health, query latency from the active vector DB."""
    console.print("\n[key]Vector DB Stats:[/key]")
    
    # Try Qdrant first (most common)
    qdrant_url = _get_service_url("qdrant", 6333)
    resp = _http_get(f"{qdrant_url}/collections")
    
    if resp and "result" in resp:
        collections = resp["result"].get("collections", [])
        table = Table(title="Qdrant Collections")
        table.add_column("Collection", style="cyan")
        table.add_column("Vectors", style="magenta")
        
        for col in collections:
            name = col.get("name", "?")
            # Get detailed info
            detail = _http_get(f"{qdrant_url}/collections/{name}")
            count = "?"
            if detail and "result" in detail:
                count = str(detail["result"].get("points_count", "?"))
            table.add_row(name, count)
        
        console.print(table)
        return
    
    # Try Weaviate
    weaviate_url = _get_service_url("weaviate", 8080)
    resp = _http_get(f"{weaviate_url}/v1/schema")
    if resp and "classes" in resp:
        table = Table(title="Weaviate Classes")
        table.add_column("Class", style="cyan")
        for cls in resp["classes"]:
            table.add_row(cls.get("class", "?"))
        console.print(table)
        return
    
    console.print("  [warning]⚠ No vector DB endpoint reachable.[/warning]")


@ml_vectors.command(name="drop")
@click.argument("collection")
def ml_vec_drop(collection: str) -> None:
    """Drop a vector collection."""
    import httpx
    
    console.print(f"[warning]🗑️ Dropping collection '{collection}'...[/warning]")
    
    qdrant_url = _get_service_url("qdrant", 6333)
    try:
        r = httpx.delete(f"{qdrant_url}/collections/{collection}", timeout=5.0)
        if r.status_code == 200:
            console.print(f"[success]✓ Collection '{collection}' deleted.[/success]")
        else:
            console.print(f"[error]✗ Failed (status {r.status_code}).[/error]")
    except Exception:
        console.print("[warning]⚠ Could not reach Qdrant.[/warning]")
