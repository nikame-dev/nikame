from typing import Optional
from fastapi import Security, Security, Query, Header
from fastapi.security import APIKeyQuery, APIKeyHeader
from app.core.error_handlers import UnauthorizedException

api_key_query = APIKeyQuery(name="api_key", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# In reality, this should be fetched from a database securely checking hashes
VALID_API_KEYS = {
    "test-key-123": "system-user",
    "prod-key-456": "external-service",
}

async def get_api_key(
    api_key_query: str = Security(api_key_query),
    api_key_header: str = Security(api_key_header),
) -> str:
    """
    Get and validate the API key from either the query string or the header.
    Expects `?api_key=...` or `X-API-Key: ...`
    """
    if api_key_query:
        api_key_value = api_key_query
    elif api_key_header:
        api_key_value = api_key_header
    else:
        raise UnauthorizedException(detail="Could not validate credentials: API Key missing")
        
    # TODO: Replace with DB call to validate API key
    if api_key_value not in VALID_API_KEYS:
        raise UnauthorizedException(detail="Could not validate credentials: API Key invalid")
        
    # Returns the identity associated with this key
    return VALID_API_KEYS[api_key_value]

async def require_api_key(key: str = Security(get_api_key)) -> str:
    """
    Dependency to enforce API key presence.
    Returns the user identifiers to the route.
    """
    return key
