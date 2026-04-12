from typing import Protocol, AsyncIterator, List, Dict

class LLMProvider(Protocol):
    async def complete(
        self,
        messages: List[Dict[str, str]],
        system: str,
        stream: bool = False,
    ) -> str | AsyncIterator[str]: ...

    async def health_check(self) -> bool: ...

    @property
    def model_name(self) -> str: ...
