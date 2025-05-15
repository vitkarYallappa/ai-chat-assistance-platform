from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel
from typing import Dict, Any, List
import time

from app.api.dependencies import (
    get_settings_dependency,
    get_channel_factory,
    get_tenant_repository,
    get_message_service,
    get_correlation_id
)

# Response models
class HealthResponse(BaseModel):
    status: str
    version: str
    service: str
    timestamp: float

class DetailedHealthResponse(HealthResponse):
    dependencies: Dict[str, Dict[str, Any]]
    channels: Dict[str, bool]

# Router
router = APIRouter()

@router.get(
    "/",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Returns basic health status of the service",
    status_code=status.HTTP_200_OK
)
async def get_health(
    request: Request,
    settings = Depends(get_settings_dependency),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Basic health check endpoint.
    
    Returns a simple health status indicating the service is running.
    """
    return {
        "status": "ok",
        "version": "0.1.0",  # Should be retrieved from a version file or env var
        "service": settings.APP_NAME,
        "timestamp": time.time()
    }

@router.get(
    "/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed health check",
    description="Returns detailed health status including dependencies",
    status_code=status.HTTP_200_OK
)
async def get_detailed_health(
    request: Request,
    settings = Depends(get_settings_dependency),
    channel_factory = Depends(get_channel_factory),
    tenant_repository = Depends(get_tenant_repository),
    message_service = Depends(get_message_service),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Detailed health check endpoint.
    
    Returns detailed health status including the status of dependencies
    such as database connections, external services, and channel availability.
    """
    # Check database connection
    db_status = await check_database_health(tenant_repository)
    
    # Check chat service connection
    chat_service_status = await check_chat_service_health(settings.CHAT_SERVICE_URL)
    
    # Check channel availability
    channels_status = await check_channels_health(channel_factory)
    
    # Combine dependency status
    dependencies = {
        "database": db_status,
        "chat_service": chat_service_status
    }
    
    return {
        "status": "ok" if all(dep["status"] == "ok" for dep in dependencies.values()) else "degraded",
        "version": "0.1.0",  # Should be retrieved from a version file or env var
        "service": settings.APP_NAME,
        "timestamp": time.time(),
        "dependencies": dependencies,
        "channels": channels_status
    }

async def check_database_health(repository) -> Dict[str, Any]:
    """
    Checks database connection health.
    """
    try:
        # Perform a simple database query to check connectivity
        await repository.health_check()
        return {
            "status": "ok",
            "latency_ms": 0  # Should measure actual latency
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

async def check_chat_service_health(url: str) -> Dict[str, Any]:
    """
    Checks chat service health by calling its health endpoint.
    """
    try:
        # Use httpx or similar library to make a request to chat service health endpoint
        # This is a mock implementation
        return {
            "status": "ok",
            "latency_ms": 0  # Should measure actual latency
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

async def check_channels_health(channel_factory) -> Dict[str, bool]:
    """
    Checks availability of all enabled channels.
    """
    channels = channel_factory.get_all_channels()
    result = {}
    
    for channel_id, channel in channels.items():
        try:
            # Check if channel is available
            is_available = await channel.is_available()
            result[channel_id] = is_available
        except Exception:
            result[channel_id] = False
    
    return result