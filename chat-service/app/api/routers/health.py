from fastapi import APIRouter, Depends, status
from typing import Dict, Any
from datetime import datetime

from app.config import get_settings
from app.utils.logger import LoggerAdapter
from app.api.dependencies import get_request_logger_dependency

settings = get_settings()
router = APIRouter(prefix="/health")


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    response_description="Service health status"
)
async def get_health() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        Dict: Basic service health information
    """
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get(
    "/detailed",
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    response_description="Detailed service health status"
)
async def get_detailed_health(
    logger: LoggerAdapter = Depends(get_request_logger_dependency)
) -> Dict[str, Any]:
    """
    Detailed health check endpoint including dependency status.
    
    Args:
        logger: Request logger
        
    Returns:
        Dict: Detailed service health information
    """
    logger.info("Performing detailed health check")
    
    # Define health checks for dependencies
    # TODO: Implement actual health checks for dependencies
    dependencies = {
        "database": check_database_health(),
        "cache": check_cache_health(),
        "adaptor_service": check_external_service_health("adaptor_service"),
        "mcp_service": check_external_service_health("mcp_service")
    }
    
    # Determine overall status
    overall_status = "ok"
    if any(dep["status"] != "ok" for dep in dependencies.values()):
        if any(dep["status"] == "error" for dep in dependencies.values()):
            overall_status = "error"
        else:
            overall_status = "degraded"
    
    return {
        "status": overall_status,
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": dependencies
    }


def check_database_health() -> Dict[str, Any]:
    """
    Check database connection health.
    
    Returns:
        Dict: Database health status
    """
    # TODO: Implement actual database health check
    return {
        "status": "ok",
        "latency_ms": 5,
        "message": "Database connection established"
    }


def check_cache_health() -> Dict[str, Any]:
    """
    Check cache connection health.
    
    Returns:
        Dict: Cache health status
    """
    # TODO: Implement actual cache health check
    return {
        "status": "ok",
        "latency_ms": 2,
        "message": "Cache connection established"
    }


def check_external_service_health(service_name: str) -> Dict[str, Any]:
    """
    Check external service health.
    
    Args:
        service_name: Name of the external service
        
    Returns:
        Dict: External service health status
    """
    # TODO: Implement actual external service health check
    return {
        "status": "ok",
        "latency_ms": 15,
        "message": f"{service_name} connection established"
    }