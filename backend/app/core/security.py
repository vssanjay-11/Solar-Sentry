from typing import Optional
from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings
from app.core.logging import logger

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    x_api_key: Optional[str] = Security(api_key_header),
    authorization: Optional[str] = Header(default=None)
) -> str:
    """Validate API key or Bearer token if REQUIRE_API_KEY is enabled."""
    if not settings.REQUIRE_API_KEY:
        return "development_bypass"

    token = x_api_key
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials (X-API-Key or Bearer token required)."
        )

    valid_keys = {settings.API_KEY, settings.EDGE_API_KEY}
    if token not in valid_keys:
        logger.warning(f"Unauthorized access attempt with invalid token: {token[:4]}***")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired API Key."
        )

    return "authenticated_client"
