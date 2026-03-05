"""ML Model Manager for NIKAME.

Handles model metadata, source resolution (HuggingFace, Ollama, Custom),
and versioning.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from nikame.exceptions import NikameError


@dataclass
class ModelSource:
    """Metadata for a model source."""
    type: Literal["huggingface", "ollama", "custom", "openai_compatible", "onnx", "replicate"]
    identifier: str  # repo name, model tag, or path
    revision: str = "main"
    token_env_var: str | None = None


class ModelManager:
    """Manages ML model lifecycle and source resolution."""

    def __init__(self, cache_dir: str | None = None) -> None:
        self.cache_dir = cache_dir or os.path.expanduser("~/.nikame/models")
        os.makedirs(self.cache_dir, exist_ok=True)

    def resolve_source(self, model_name: str, config: dict[str, Any]) -> ModelSource:
        """Determine the source and identifier from config."""
        source_type = config.get("source", "huggingface")

        if source_type == "huggingface":
            identifier = config.get("model")
            if not identifier:
                raise NikameError(f"Model '{model_name}' missing 'model' field for HuggingFace source.")
            return ModelSource(
                type="huggingface",
                identifier=identifier,
                revision=config.get("revision", "main"),
                token_env_var=config.get("token")
            )

        elif source_type == "ollama":
            identifier = config.get("model")
            if not identifier:
                raise NikameError(f"Model '{model_name}' missing 'model' field for Ollama source.")
            return ModelSource(type="ollama", identifier=identifier)

        elif source_type == "custom":
            path = config.get("path")
            if not path:
                raise NikameError(f"Model '{model_name}' missing 'path' field for custom source.")
            return ModelSource(type="custom", identifier=path)

        elif source_type == "openai_compatible":
            base_url = config.get("base_url")
            model = config.get("model")
            if not base_url or not model:
                raise NikameError(f"Model '{model_name}' missing 'base_url' or 'model' for OpenAI source.")
            return ModelSource(type="openai_compatible", identifier=f"{base_url}|{model}")

        return ModelSource(type=source_type, identifier=config.get("model", config.get("path", "")))

    def get_download_path(self, source: ModelSource) -> str:
        """Get the local path where the model should be stored."""
        safe_id = source.identifier.replace("/", "_").replace(":", "_").replace("|", "_")
        return os.path.join(self.cache_dir, f"{source.type}_{safe_id}")
