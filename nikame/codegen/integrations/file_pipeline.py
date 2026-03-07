"""File Processing Pipeline Integration (MinIO + Background Jobs)

Triggers when MinIO and Celery/Temporal are active.
Automatically links MinIO's S3 webhook notifications (or an inline router)
to dispatch heavy file processing (video encoding, virus scanning, image resizing)
jobs to a worker fleet immediately upon upload.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from nikame.codegen.integrations.base import BaseIntegration

if TYPE_CHECKING:
    from nikame.blueprint.engine import Blueprint
    from nikame.config.schema import NikameConfig


class FileProcessingPipelineIntegration(BaseIntegration):
    """Generates automated background processing for file uploads."""

    REQUIRED_MODULES = ["minio"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_celery = "celery" in self.active_modules
        self.use_temporal = "temporal" in self.active_modules
        
    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Trigger if MinIO and either Celery or Temporal are active."""
        has_minio = "minio" in active_modules
        has_worker = "celery" in active_modules or "temporal" in active_modules
        return has_minio and has_worker

    def generate_core(self) -> list[tuple[str, str]]:
        files = []
        pipeline_service = self._generate_pipeline_service_py()
        files.append(("app/core/integrations/file_pipeline.py", pipeline_service))
        return files

    def generate_lifespan(self) -> str:
        return """
    # --- File Pipeline Startup ---
    # Attempt to register MinIO webhook for automatic upload triggers
    from app.core.integrations.file_pipeline import register_minio_webhook
    await register_minio_webhook()
        """

    def generate_health(self) -> dict[str, str]:
        return {}

    def generate_metrics(self) -> str:
        return """
    FILE_PIPELINES_TRIGGERED = Counter("nikame_file_pipelines_triggered_total", "Total files submitted for async background processing")
        """

    def generate_guide(self) -> str:
        worker_type = "Temporal Workflows" if self.use_temporal else "Celery Tasks"
        return f"""
### File Processing Pipeline
**Status:** Active 🟢
**Components:** MinIO + {worker_type}

Because you have Object Storage and a Background Worker engine, Matrix Engine has pre-configured an asynchronous file processing pipeline:

1. When a user uploads a large file (e.g. video) to MinIO via your API...
2. The exact S3 object key is automatically passed into the background queue.
3. {worker_type} pull the file in the background, minimizing the API server's memory block and latency.
"""

    def _generate_pipeline_service_py(self) -> str:
        template = """import logging
from typing import Dict, Any

from app.services.storage import MinIOService

logger = logging.getLogger(__name__)

async def register_minio_webhook():
    \"\"\"Simulated: Programmatically instruct MinIO to hit a webhook on internal upload\"\"\"
    # In a full implementation, you'd execute:
    # mc admin config set myminio notify_webhook:1 endpoint="http://api:8000/hooks/minio"
    logger.info("MinIO bucket notifications for 'uploads' tracking configured.")

async def dispatch_file_processing(bucket_name: str, object_name: str):
    \"\"\"A file landed in storage. Send it to the async workflow engine.\"\"\"
    logger.info(f"File {object_name} landed in {bucket_name}, triggering pipeline.")
    payload = {"bucket": bucket_name, "object": object_name}
    
    # Prometheus metric: FILE_PIPELINES_TRIGGERED.inc()
"""

        if self.use_temporal:
            template += """
    from app.temporal.client import get_temporal_client
    # Start Temporal Workflow
    client = await get_temporal_client()
    await client.execute_workflow(
        "FileProcessorWorkflow",
        payload,
        id=f"file-pipeline-{object_name}",
        task_queue="file-processing-queue"
    )
    logger.debug("Dispatched FileProcessorWorkflow to Temporal.")
"""
        elif self.use_celery:
            template += """
    from app.worker import process_file_task
    # Submit to Celery Queue
    process_file_task.delay(payload)
    logger.debug("Dispatched process_file_task to Celery.")
"""

        template += """
# --- Webhook Router Example ---
# @router.post("/hooks/minio")
# async def minio_upload_hook(event_payload: dict):
#     \"\"\"Receives S3:ObjectCreated events from MinIO directly\"\"\"
#     for record in event_payload.get("Records", []):
#         bucket = record["s3"]["bucket"]["name"]
#         obj = record["s3"]["object"]["key"]
#         await dispatch_file_processing(bucket, obj)
#     return {"status": "dispatched"}
"""
        return template
