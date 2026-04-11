"""
Factory Dependency Pattern.

Provides a dependency that reads from the application configuration
and dynamically returns the correct concrete implementation for an interface.
Useful for swapping email providers, payment gateways, or LLM providers
without changing route logic.
"""
from typing import Protocol

from fastapi import Depends, Request

from {{APP_NAME}}.core.settings import settings


class StorageProvider(Protocol):
    """Interface that all storage providers must implement."""
    async def save(self, filename: str, data: bytes) -> str:
        ...


class LocalStorageProvider:
    async def save(self, filename: str, data: bytes) -> str:
        return f"file:///local/path/{filename}"


class S3StorageProvider:
    async def save(self, filename: str, data: bytes) -> str:
        return f"s3://bucket-name/{filename}"


# Define globally because it is stateless, but if it needs Request 
# or DB context, you can assemble it inside the provider generator.
_LOCAL_STORAGE = LocalStorageProvider()
_S3_STORAGE = S3StorageProvider()


async def get_storage_provider(request: Request) -> StorageProvider:
    """
    Factory dependency.
    
    Reads config from the environment and yields the appropriate
    implementation class that conforms to the StorageProvider protocol.
    """
    provider_config = getattr(settings, "STORAGE_PROVIDER", "local")
    
    if provider_config == "s3":
        return _S3_STORAGE
    elif provider_config == "local":
        return _LOCAL_STORAGE
    else:
        raise ValueError(f"Unknown storage provider config: {provider_config}")


# Usage in a router:
# @router.post("/upload")
# async def upload_file(
#     file_data: bytes, 
#     storage: StorageProvider = Depends(get_storage_provider)
# ):
#     # The router does not need to know which provider is active.
#     url = await storage.save("my_file.txt", file_data)
#     return {"url": url}
