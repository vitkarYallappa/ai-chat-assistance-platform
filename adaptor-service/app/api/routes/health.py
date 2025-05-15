from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Dict, List, Optional

from app.api.dependencies import (
    get_adaptor_factory,
    get_cache_service,
    get_auth_service
)
from app.core.logging import get_logger

# Initialize router and logger
health_router = APIRouter()
logger = get_logger(__name__)


class HealthStatus(BaseModel):
    """Basic health status response model."""
    status: str
    version: str = "0.1.0"
    service: str = "Adaptor Service"


class DependencyStatus(BaseModel):
    """Status of a single dependency."""
    name: str
    status: str
    details: Optional[Dict] = None


class DetailedHealthStatus(HealthStatus):
    """Detailed health status with dependency information."""
    dependencies: List[DependencyStatus]


@health_router.get(
    "",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Returns basic health status of the service."
)
async def get_health() -> HealthStatus:
    """
    Basic health check endpoint.
    
    Returns:
        HealthStatus: Basic service health status
    """
    logger.debug("Health check requested")
    return HealthStatus(status="ok")


@health_router.get(
    "/detailed",
    response_model=DetailedHealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="Returns detailed health status including dependencies."
)
async def get_detailed_health(
    adaptor_factory: Dict = Depends(get_adaptor_factory),
    cache_service: Dict = Depends(get_cache_service),
    auth_service: Dict = Depends(get_auth_service),
) -> DetailedHealthStatus:
    """
    Detailed health check endpoint with dependency status.
    
    Args:
        adaptor_factory: Adaptor factory dependency
        cache_service: Cache service dependency
        auth_service: Auth service dependency
        
    Returns:
        DetailedHealthStatus: Detailed service health with dependencies status
    """
    logger.debug("Detailed health check requested")
    
    # In a real implementation, we would actually check the health of each dependency
    # For now, we'll just return placeholder statuses
    dependencies = [
        DependencyStatus(
            name="adaptor_factory",
            status="ok",
            details={"info": "Placeholder for adaptor factory status"}
        ),
        DependencyStatus(
            name="cache_service",
            status="ok",
            details={"info": "Placeholder for cache service status"}
        ),
        DependencyStatus(
            name="auth_service",
            status="ok",
            details={"info": "Placeholder for auth service status"}
        ),
    ]
    
    return DetailedHealthStatus(
        status="ok",
        dependencies=dependencies
    )