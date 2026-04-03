"""
MLflow experiment tracking client.
"""
import mlflow
import os
from core.config import settings

def init_tracking():
    """Initialize MLflow tracking URI and default experiment."""
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    # Ensure S3 endpoint is set for artifacts
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = settings.MLFLOW_S3_ENDPOINT_URL
    os.environ["AWS_ACCESS_KEY_ID"] = settings.MINIO_ACCESS_KEY
    os.environ["AWS_SECRET_ACCESS_KEY"] = settings.MINIO_SECRET_KEY
    
    mlflow.set_experiment(settings.APP_NAME)
