"""
NIKAME LLM Gateway.
Unified interface for LLM completions and embeddings.
"""
import os
import httpx
from typing import Any, List, Optional

class LLMGateway:
    """Singleton gateway for all LLM interactions."""
    
    @classmethod
    async def generate_completion(cls, prompt: str, **kwargs) -> str:
        """Generate a text completion."""
        # Simple implementation for generated stub
        # In a real setup, this routes via model_manager
        return "NIKAME Generated Response"

    @classmethod
    async def generate_embedding(cls, text: str) -> List[float]:
        """Generate a vector embedding for the given text."""
        # Return a dummy 384-dim vector (SBERT size)
        return [0.1] * 384
