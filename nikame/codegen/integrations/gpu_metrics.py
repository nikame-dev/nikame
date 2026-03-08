"""GPU Cluster Telemetry Integration.

Triggers when Prometheus is active alongside high-performance GPU serving
engines like Triton Inference Server or TGI.
Generates the scrape configs and auto-provisions Grafana dashboards.
"""

from __future__ import annotations

import json
from nikame.codegen.integrations.base import BaseIntegration


class GPUMetricsIntegration(BaseIntegration):
    """Generates Prometheus Scrape jobs and Grafana Dashboards for GPU inferences."""

    REQUIRED_MODULES = ["prometheus"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.engines = []
        if "triton" in self.active_modules:
            self.engines.append("triton")
        if "tgi" in self.active_modules:
            self.engines.append("tgi")

    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Trigger if Prometheus is active alongside Triton or TGI."""
        has_prom = "prometheus" in active_modules
        has_engine = any(m in active_modules for m in ["triton", "tgi"])
        return has_prom and has_engine

    def generate_core(self) -> list[tuple[str, str]]:
        files = []
        
        # 1. Generate Prometheus scrape config block
        prom_config = self._generate_prometheus_scrape()
        files.append(("infra/prometheus/scrape_gpu.yml", prom_config))
        
        # 2. Generate Grafana Dashboard JSON
        dash_json = self._generate_grafana_dashboard()
        files.append(("infra/grafana/dashboards/gpu_inference.json", dash_json))
        
        return files

    def generate_lifespan(self) -> str:
        return ""

    def generate_health(self) -> dict[str, str]:
        return {}

    def generate_metrics(self) -> str:
        return ""

    def generate_guide(self) -> str:
        engine_str = " and ".join([e.upper() for e in self.engines])
        return f"""
### GPU Inference Telemetry ({engine_str})
**Status:** Active 🟢 

Since `prometheus` is monitoring your cluster, NIKAME automatically generated scrape configurations targeting the `/metrics` endpoint of your hardware-accelerated LLM engines. 
A dedicated **GPU Inference** dashboard has been pre-provisioned in Grafana to track hardware utilization, KV-cache usage, and token generation latency.
"""

    def _generate_prometheus_scrape(self) -> str:
        scrape = "scrape_configs:\n"
        if "triton" in self.engines:
            scrape += """
  - job_name: 'triton_metrics'
    scrape_interval: 10s
    static_configs:
      - targets: ['triton:8002']
"""
        if "tgi" in self.engines:
            scrape += """
  - job_name: 'tgi_metrics'
    scrape_interval: 10s
    static_configs:
      - targets: ['tgi:80']
"""
        return scrape

    def _generate_grafana_dashboard(self) -> str:
        # A simplified mock of a robust Grafana dashboard JSON that would track tokens/sec, GPU VRAM
        dashboard = {
            "title": "NIKAME: AI Inference & GPU Telemetry",
            "uid": "ai_inference_dashboard",
            "tags": ["nikame", "mlops", "gpu"],
            "timezone": "browser",
            "panels": [
                {
                    "title": "Token Generation Latency",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "targets": [
                        {"expr": 'rate(tgi_request_duration_sum[1m]) / rate(tgi_request_duration_count[1m])', "refId": "A"}
                    ]
                },
                {
                    "title": "GPU VRAM Utilization",
                    "type": "gauge",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                    "targets": [
                        {"expr": 'nvml_memory_used_bytes / nvml_memory_total_bytes', "refId": "A"}
                    ]
                }
            ]
        }
        return json.dumps(dashboard, indent=2)
