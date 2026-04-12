from collections.abc import AsyncIterator
from typing import Protocol


class LLMProvider(Protocol):
    """Protocol for AI model providers."""

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """
        Generates a completion from the LLM.
        
        Args:
            messages: List of chat messages (role/content).
            system: System prompt instruction.
            stream: Whether to stream the response.
            
        Returns:
            Either a full string response or an async iterator of tokens.
        """
        ...

    async def health_check(self) -> bool:
        """Checks if the provider service is reachable."""
        ...

    @property
    def model_name(self) -> str:
        """Returns the name of the model being used."""
        ...
