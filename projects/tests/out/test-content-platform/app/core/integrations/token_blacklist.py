import logging
from typing import Optional
from fastapi import HTTPException, status

from app.services.cache import DragonflyService

logger = logging.getLogger(__name__)

async def revoke_token(token_signature: str, exp_seconds: int) -> None:
    """Add a JWT signature to the distributed revocation list.
    
    The token will automatically expire from the blacklist at the same time
    the JWT itself mathematically expires, saving memory.
    """
    cache_key = f"auth:blacklist:{token_signature}"
    await DragonflyService.set(cache_key, "revoked", expire=exp_seconds)
    logger.info("JWT inserted into revocation blacklist.")
    # Prometheus Metric: TOKENS_REVOKED.inc()

async def is_token_revoked(token_signature: str) -> bool:
    """Check if a JWT is on the blocklist."""
    cache_key = f"auth:blacklist:{token_signature}"
    is_revoked = await DragonflyService.exists(cache_key)
    
    if is_revoked:
        logger.warning("Attempted use of revoked JWT blocked.")
        # Prometheus Metric: REVOKED_TOKEN_REJECTIONS.inc()
        return True
        
    return False

# --- Middleware Hook Example ---
# Modify app/core/security.py (or middleware) to utilize these functions
# right after mathematically validating the JWT signature.
