# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig


class CronJobsCodegen(BaseCodegen):
    NAME = "cron_jobs"
    DESCRIPTION = "Celery-backed background jobs and cron scheduler"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx, config)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "cron_jobs"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        """Generate the worker file for background jobs."""
        files = [
            ("app/worker.py", self.env.get_template("worker.py.j2").render()),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            requirements=["celery[redis]>=5.3.0"]
        )

    def k8s_manifests(self) -> list[dict[str, Any]]:
        """Generate K8s CronJob manifest for this component."""
        name = "cron-worker"
        return [{
            "apiVersion": "batch/v1",
            "kind": "CronJob",
            "metadata": {"name": name, "namespace": self.ctx.project_name}, # Simplified namespace
            "spec": {
                "schedule": "*/5 * * * *", # Default every 5 mins
                "jobTemplate": {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [{
                                    "name": name,
                                    "image": f"{self.ctx.project_name}-api:latest",
                                    "command": ["celery", "-A", "app.worker", "worker", "--loglevel=info"],
                                    "envFrom": [{"configMapRef": {"name": "api-config"}}]
                                }],
                                "restartPolicy": "OnFailure"
                            }
                        }
                    }
                }
            }
        }]
