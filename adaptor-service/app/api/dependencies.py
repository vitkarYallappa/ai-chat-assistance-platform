from fastapi import Depends, Header, HTTPException, status
from typing import Annotated, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


async def get_adaptor_factory():
    """
    Dependency for providing the adaptor factory.
    
    This will be implemented fully when the adaptor factory is created.
    
    Returns:
        A placeholder for the adaptor factory
    """
    # This is a placeholder that will be replaced when we implement
    # the actual adaptor factory in a later phase
    return {"status": "factory_placeholder"}


async def get_cache_service():
    """
    Dependency for providing the caching service.
    
    This will be implemented fully when the cache service is created.
    
    Returns:
        A placeholder for the cache service
    """
    # This is a placeholder that will be replaced when we implement
    # the actual cache service in a later phase
    return {"status": "cache_service_placeholder"}


async def get_auth_service():
    """
    Dependency for providing the authentication service.
    
    This will be implemented fully when the auth service is created.
    
    Returns:
        A placeholder for the auth service
    """
    # This is a placeholder that will be replaced when we implement
    # the actual auth service in a later phase
    return {"status": "auth_service_placeholder"}


async def get_current_tenant(
    x_tenant_id: Annotated[Optional[str], Header()] = None
) -> str:
    """
    Extract tenant info from request header.
    
    Args:
        x_tenant_id: Optional tenant ID from X-Tenant-ID header
        
    Returns:
        str: The tenant ID to use
        
    Raises:
        HTTPException: If tenant ID is missing and required
    """
    settings = get_settings()
    
    # If tenant ID is not provided, use default
    if not x_tenant_id:
        logger.debug(f"No tenant ID provided, using default: {settings.DEFAULT_TENANT_ID}")
        return settings.DEFAULT_TENANT_ID
    
    # In the future, we might validate tenant IDs against a database
    # For now, we'll accept any non-empty tenant ID
    if not x_tenant_id.strip():
        logger.warning("Empty tenant ID provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID cannot be empty"
        )
    
    logger.debug(f"Using tenant ID: {x_tenant_id}")
    return x_tenant_id