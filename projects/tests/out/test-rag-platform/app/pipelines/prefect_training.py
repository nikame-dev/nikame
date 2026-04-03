import mlflow
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
