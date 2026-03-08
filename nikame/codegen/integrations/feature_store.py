"""Feast Feature Store Retrieval Integration.

Triggers when Feast is active alongside an orchestration framework.
Wires point-in-time correct feature retrieval logic directly into the 
generated training pipeline script.
"""

from __future__ import annotations

from nikame.codegen.integrations.base import BaseIntegration


class FeatureStoreIntegration(BaseIntegration):
    """Generates Feast point-in-time retrieval logic."""

    REQUIRED_MODULES = ["feast"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.orchestrator = "python"
        if "prefect" in self.active_modules:
            self.orchestrator = "prefect"
        elif "airflow" in self.active_modules:
            self.orchestrator = "airflow"
        elif "zenml" in self.active_modules:
            self.orchestrator = "zenml"

    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Trigger if Feast is active alongside any Orchestrator."""
        has_feast = "feast" in active_modules
        has_orchestrator = any(m in active_modules for m in ["prefect", "airflow", "zenml", "mlflow"])
        return has_feast and has_orchestrator

    def generate_core(self) -> list[tuple[str, str]]:
        # This supplements the orchestration scripts generated in orchestration.py
        # We output a discrete helper for getting the historical features.
        files = []
        files.append(("app/pipelines/feature_retrieval.py", self._generate_retrieval()))
        return files

    def generate_lifespan(self) -> str:
        return ""

    def generate_health(self) -> dict[str, str]:
        return {}

    def generate_metrics(self) -> str:
        return ""

    def generate_guide(self) -> str:
        return f"""
### Feature Retrieval (Feast)
**Status:** Active 🟢 
**Pipeline Engine:** `{self.orchestrator}`

A helper module `app.pipelines.feature_retrieval` has been generated. It configures the Feast `FeatureStore` client to retrieve point-in-time correct training datasets natively inside your `{self.orchestrator}` directed acyclic graphs.
"""

    def _generate_retrieval(self) -> str:
        return """import logging
from datetime import datetime
import pandas as pd
from feast import FeatureStore

logger = logging.getLogger(__name__)

def get_historical_features(entity_df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    \"\"\"
    Retrieve point-in-time correct features for training.
    
    Args:
        entity_df: A Pandas DataFrame containing entity IDs and event timestamps.
                   Example: columns=['driver_id', 'event_timestamp']
        features: List of feature strings.
                  Example: ['driver_hourly_stats:conv_rate']
                  
    Returns:
        A joined Pandas DataFrame containing the original entities + requested features.
    \"\"\"
    try:
        # Assuming repo path is mounted to a known volume
        store = FeatureStore(repo_path="feature_repo/")
        
        training_df = store.get_historical_features(
            entity_df=entity_df,
            features=features
        ).to_df()
        
        logger.info(f"Retrieved {len(features)} features for {len(entity_df)} entities.")
        return training_df
    except Exception as e:
        logger.error(f"Failed to retrieve Feast features: {e}")
        return pd.DataFrame()
"""
