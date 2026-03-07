"""Auth Token Blacklist Integration (Auth + Dragonfly)

Triggers when an Authentication module (Keycloak/Authentik) and 
Dragonfly (Redis) are active. Generates a distributed token 
revocation list to handle instant logout across stateless APIs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from nikame.codegen.integrations.base import BaseIntegration

if TYPE_CHECKING:
    from nikame.blueprint.engine import Blueprint
    from nikame.config.schema import NikameConfig


class AuthTokenBlacklistIntegration(BaseIntegration):
    """Generates distributed Token Revocation layer."""

    REQUIRED_MODULES = ["dragonfly"]
    REQUIRED_FEATURES = ["auth"]

    def generate_core(self) -> list[tuple[str, str]]:
        files = []
        blacklist_service = self._generate_blacklist_service_py()
        files.append(("app/core/integrations/token_blacklist.py", blacklist_service))
        return files

    def generate_lifespan(self) -> str:
        return "" 

    def generate_health(self) -> dict[str, str]:
        return {} 

    def generate_metrics(self) -> str:
        return """
    TOKENS_REVOKED = Counter(
        "nikame_auth_tokens_revoked_total", 
        "Total JWT tokens explicitly revoked"
    )
    REVOKED_TOKEN_REJECTIONS = Counter(
        "nikame_auth_revoked_token_rejections_total", 
        "Total API requests rejected due to blacklisted token"
    )
        """

    def generate_guide(self) -> str:
        return """
### Token Revocation List (Blacklist)
**Status:** Active 🟢
**Components:** Auth + Dragonfly

Because you selected Auth alongside a Cache, stateless JWTs can now be instantly revoked. 
When a user logs out, their token signature is inserted into Dragonfly. The authentication middleware will automatically check this fast-cache before trusting any valid JWT signatures.
"""

    def _generate_blacklist_service_py(self) -> str:
        return """import logging
from typing import Optional
from fastapi import HTTPException, status

from app.services.cache import DragonflyService

logger = logging.getLogger(__name__)

async def revoke_token(token_signature: str, exp_seconds: int) -> None:
    \"\"\"Add a JWT signature to the distributed revocation list.
    
    The token will automatically expire from the blacklist at the same time
    the JWT itself mathematically expires, saving memory.
    \"\"\"
    cache_key = f"auth:blacklist:{token_signature}"
    await DragonflyService.set(cache_key, "revoked", expire=exp_seconds)
    logger.info("JWT inserted into revocation blacklist.")
    # Prometheus Metric: TOKENS_REVOKED.inc()

async def is_token_revoked(token_signature: str) -> bool:
    \"\"\"Check if a JWT is on the blocklist.\"\"\"
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
"""
