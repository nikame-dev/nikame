"""Pipeline Orchestration Integration.

Triggers when Prefect, Airflow, or ZenML is active alongside MLflow.
Wires native training/ETL pipeline scripts that utilize MLflow for experiment tracking.
"""

from __future__ import annotations

from nikame.codegen.integrations.base import BaseIntegration


class OrchestrationIntegration(BaseIntegration):
    """Generates Orchestrator + MLflow training pipelines."""

    REQUIRED_MODULES = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if "prefect" in self.active_modules:
            self.orchestrator = "prefect"
        elif "airflow" in self.active_modules:
            self.orchestrator = "airflow"
        elif "zenml" in self.active_modules:
            self.orchestrator = "zenml"
        else:
            self.orchestrator = None

    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Trigger if MLflow and any Orchestrator is present."""
        has_mlflow = "mlflow" in active_modules
        has_orchestrator = any(m in active_modules for m in ["prefect", "airflow", "zenml"])
        return has_mlflow and has_orchestrator

    def generate_core(self) -> list[tuple[str, str]]:
        if not self.orchestrator:
            return []
            
        if self.orchestrator == "prefect":
            code = self._generate_prefect()
            path = "app/pipelines/prefect_training.py"
        elif self.orchestrator == "airflow":
            code = self._generate_airflow()
            path = "dags/airflow_training.py"
        else:
            code = self._generate_zenml()
            path = "app/pipelines/zenml_training.py"
            
        return [(path, code)]

    def generate_lifespan(self) -> str:
        return ""

    def generate_health(self) -> dict[str, str]:
        return {}

    def generate_metrics(self) -> str:
        return ""

    def generate_guide(self) -> str:
        return f"""
### ML Training Orchestration ({self.orchestrator.capitalize()} + MLflow)
**Status:** Active 🟢 
**Pipeline Engine:** `{self.orchestrator}`

A fully wired example training pipeline is generated for your selected orchestrator. The pipeline automatically logs parameters, metrics, and models to the local `MLflow` backend tracking server.
"""

    def _generate_prefect(self) -> str:
        return """import mlflow
from prefect import flow, task
from app.core.config import settings

@task
def load_data():
    return {"X": [1, 2, 3], "y": [2, 4, 6]}

@task
def train_model(data):
    # Dummy training logic
    return {"coef": 2.0}

@flow(name="MLflow-Prefect-Training")
def training_pipeline():
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    mlflow.set_experiment("prefect-experiment")
    
    with mlflow.start_run():
        data = load_data()
        mlflow.log_param("dataset_size", len(data["X"]))
        
        model = train_model(data)
        mlflow.log_metric("coef", model["coef"])
        
        # Log model (simplified)
        mlflow.log_dict(model, "model_params.json")

if __name__ == "__main__":
    training_pipeline()
"""

    def _generate_airflow(self) -> str:
        return """from datetime import datetime
from airflow import DAG
from airflow.decorators import task
import mlflow
import os

# Assuming MLFLOW_TRACKING_URI is set in the Airflow worker environment
TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")

with DAG(
    dag_id='mlflow_training_pipeline',
    start_date=datetime(2023, 1, 1),
    schedule_interval='@daily',
    catchup=False
) as dag:

    @task
    def load_data():
        return {"X": [1, 2, 3], "y": [2, 4, 6]}

    @task
    def train_and_log(data: dict):
        mlflow.set_tracking_uri(TRACKING_URI)
        mlflow.set_experiment("airflow-experiment")
        
        with mlflow.start_run():
            mlflow.log_param("dataset_size", len(data["X"]))
            model = {"coef": 2.0} # Dummy model
            mlflow.log_metric("coef", model["coef"])
            mlflow.log_dict(model, "model_params.json")
            
        return "success"

    data = load_data()
    train_and_log(data)
"""

    def _generate_zenml(self) -> str:
        return """from zenml import pipeline, step
import mlflow
from app.core.config import settings

@step
def load_data() -> dict:
    return {"X": [1, 2, 3], "y": [2, 4, 6]}

@step(experiment_tracker="mlflow_tracker")
def train_model(data: dict) -> dict:
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    mlflow.log_param("dataset_size", len(data["X"]))
    
    model = {"coef": 2.0} # Dummy
    mlflow.log_metric("coef", model["coef"])
    return model

@pipeline
def ml_training_pipeline():
    data = load_data()
    train_model(data)

if __name__ == "__main__":
    ml_training_pipeline()
"""
