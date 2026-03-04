"""Serving selection logic for NIKAME MLOps.

Matches models and hardware to the most efficient serving backend.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from nikame.mlops.hardware import HardwareSpecs
    from nikame.config.schema import MLModelConfig


ServingBackend = Literal["vllm", "ollama", "triton", "llamacpp", "bentoml", "airllm"]


class ServingSelector:
    """Logic to recommend a serving backend."""

    @staticmethod
    def select(model: MLModelConfig, hardware: HardwareSpecs) -> ServingBackend:
        """
        Recommend a serving backend based on model config and hardware.
        """
        # 1. User override takes precedence
        if model.serve_with != "auto":
            return model.serve_with

        # 2. Logic based on source and hardware
        if model.source == "ollama":
            return "ollama"

        if model.source == "onnx":
            return "triton"

        # 3. LLM specific logic (HuggingFace/Custom LLMs)
        # We assume models from HuggingFace are likely LLMs or Transformers
        if hardware.gpu_type == "nvidia":
            if hardware.vram_gb >= 16:
                return "vllm"
            return "llamacpp"  # llama.cpp with CUDA for smaller GPUs

        if hardware.gpu_type == "apple":
            return "llamacpp"  # Metal acceleration

        # 4. CPU-only fallbacks
        if hardware.ram_gb >= 32:
            return "llamacpp"
        
        return "airllm"  # For very memory-constrained environments

    @staticmethod
    def get_recommended_quantization(
        model: MLModelConfig, hardware: HardwareSpecs
    ) -> str:
        """Recommend quantization method."""
        if not model.quantize.enabled:
            return "none"
        
        if model.quantize.method != "auto":
            return model.quantize.method

        if hardware.gpu_type == "nvidia":
            if hardware.vram_gb >= 24:
                return "awq"
            return "gptq"

        return "gguf"  # Default for CPU/Apple/Small GPU
