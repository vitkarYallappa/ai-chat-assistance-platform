from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional

from app.domain.exceptions import (
    APIException,
    ValidationException,
    ChannelException,
    ResourceNotFoundException,
    AuthenticationException,
    AuthorizationException
)

def setup_exception_handlers(app: FastAPI) -> None:
    """
    Configure exception handlers for the application.
    """
    @app.exception_handler(APIException)
    async def handle_api_exception(request: Request, exc: APIException) -> JSONResponse:
        """
        Handles APIException instances.
        """
        return create_error_response(
            request=request,
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details
        )
    
    @app.exception_handler(ValidationException)
    async def handle_validation_exception(request: Request, exc: ValidationException) -> JSONResponse:
        """
        Handles ValidationException instances.
        """
        return create_error_response(
            request=request,
            status_code=400,
            error_code="VALIDATION_ERROR",
            message="Validation error",
            details=exc.details
        )
    
    @app.exception_handler(ChannelException)
    async def handle_channel_exception(request: Request, exc: ChannelException) -> JSONResponse:
        """
        Handles ChannelException instances.
        """
        return create_error_response(
            request=request,
            status_code=500,
            error_code="CHANNEL_ERROR",
            message=f"Channel communication error: {exc.message}",
            details=exc.details
        )
    
    @app.exception_handler(ResourceNotFoundException)
    async def handle_not_found_exception(request: Request, exc: ResourceNotFoundException) -> JSONResponse:
        """
        Handles ResourceNotFoundException instances.
        """
        return create_error_response(
            request=request,
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            message=f"Resource not found: {exc.message}",
            details=exc.details
        )
    
    @app.exception_handler(AuthenticationException)
    async def handle_authentication_exception(request: Request, exc: AuthenticationException) -> JSONResponse:
        """
        Handles AuthenticationException instances.
        """
        return create_error_response(
            request=request,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            message=f"Authentication error: {exc.message}",
            details=exc.details
        )
    
    @app.exception_handler(AuthorizationException)
    async def handle_authorization_exception(request: Request, exc: AuthorizationException) -> JSONResponse:
        """
        Handles AuthorizationException instances.
        """
        return create_error_response(
            request=request,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            message=f"Authorization error: {exc.message}",
            details=exc.details
        )
    
    @app.exception_handler(Exception)
    async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
        """
        Handles all other Exception instances.
        Logs the error and returns a generic error response.
        """
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        
        logging.error(
            f"Unhandled exception: {str(exc)}",
            exc_info=True,
            extra={"correlation_id": correlation_id}
        )
        
        return create_error_response(
            request=request,
            status_code=500,
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            details=None
        )

def create_error_response(
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    Creates a standardized error response.
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    # Log the error
    logging.error(
        f"API error: {error_code} - {message}",
        extra={
            "correlation_id": correlation_id,
            "status_code": status_code,
            "error_code": error_code,
            "details": details
        }
    )
    
    # Create response payload
    response_data = {
        "error": {
            "code": error_code,
            "message": message,
            "correlation_id": correlation_id
        }
    }
    
    if details:
        response_data["error"]["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )