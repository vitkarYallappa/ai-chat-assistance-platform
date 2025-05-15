from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    APIException,
    IntegrationException,
    ValidationException,
    NotFoundError,
)
from app.core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


async def handle_api_exception(request: Request, exc: APIException) -> JSONResponse:
    """
    Handle APIException instances.
    
    Args:
        request: FastAPI request object
        exc: APIException instance
        
    Returns:
        JSONResponse: Formatted error response
    """
    logger.error(
        f"API Exception: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "error_code": exc.code,
            "context": exc.context
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def handle_validation_exception(request: Request, exc: ValidationException) -> JSONResponse:
    """
    Handle validation errors.
    
    Args:
        request: FastAPI request object
        exc: ValidationException instance
        
    Returns:
        JSONResponse: Formatted validation error response
    """
    logger.warning(
        f"Validation error: {exc.detail}",
        extra={
            "field": exc.context.get("field") if exc.context else None,
            "context": exc.context
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def handle_not_found_exception(request: Request, exc: NotFoundError) -> JSONResponse:
    """
    Handle resource not found errors.
    
    Args:
        request: FastAPI request object
        exc: NotFoundError instance
        
    Returns:
        JSONResponse: Formatted not found error response
    """
    logger.info(
        f"Resource not found: {exc.detail}",
        extra={
            "resource_type": exc.context.get("resource_type") if exc.context else None,
            "resource_id": exc.context.get("resource_id") if exc.context else None
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def handle_integration_exception(request: Request, exc: IntegrationException) -> JSONResponse:
    """
    Handle external API integration errors.
    
    Args:
        request: FastAPI request object
        exc: IntegrationException instance
        
    Returns:
        JSONResponse: Formatted integration error response
    """
    logger.error(
        f"Integration error: {exc.detail}",
        extra={
            "original_error": exc.context.get("original_error") if exc.context else None,
            "context": exc.context
        }
    )
    
    # Remove sensitive information from the response
    # but keep it in the logs for debugging
    safe_context = exc.context.copy() if exc.context else {}
    if "auth_token" in safe_context:
        safe_context["auth_token"] = "[REDACTED]"
    if "api_key" in safe_context:
        safe_context["api_key"] = "[REDACTED]"
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.detail,
                "status_code": exc.status_code,
                "context": safe_context
            }
        }
    )