from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid
from typing import Callable

from app.core.config import get_settings, load_env_file
from app.core.exceptions import APIException
from app.core.logging import configure_logging, get_logger, set_correlation_id, set_tenant_id


# Load environment variables and configure logging early
load_env_file()
configure_logging()
logger = get_logger(__name__)


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    settings = get_settings()
    
    # Create FastAPI app with metadata
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        debug=settings.DEBUG
    )
    
    # Register middleware
    configure_middleware(app)
    
    # Register exception handlers
    handle_exceptions(app)
    
    # Register routers
    register_routers(app)
    
    # Add startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting up Adaptor Service")
        # Add any startup initialization here
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down Adaptor Service")
        # Add any cleanup operations here
    
    return app


def configure_middleware(app: FastAPI) -> None:
    """
    Configure middleware components for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    settings = get_settings()
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request tracking middleware
    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next: Callable):
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_correlation_id(correlation_id)
        
        # Extract tenant ID from header or use default
        tenant_id = request.headers.get("X-Tenant-ID") or get_settings().DEFAULT_TENANT_ID
        set_tenant_id(tenant_id)
        
        # Track request timing
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            # Log request completion
            process_time = time.time() - start_time
            logger.info(
                f"Request completed",
                extra={
                    "request_path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "process_time_ms": round(process_time * 1000, 2)
                }
            )
            
            return response
        except Exception as e:
            # Log exception and re-raise
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "request_path": request.url.path,
                    "method": request.method,
                    "process_time_ms": round(process_time * 1000, 2),
                    "error": str(e)
                },
                exc_info=True
            )
            raise


def handle_exceptions(app: FastAPI) -> None:
    """
    Configure global exception handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle custom API exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        errors = []
        for error in exc.errors():
            errors.append({
                "loc": error["loc"],
                "msg": error["msg"],
                "type": error["type"]
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation error",
                    "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "context": {
                        "errors": errors
                    }
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
                }
            }
        )


def register_routers(app: FastAPI) -> None:
    """
    Register API routers with the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    settings = get_settings()
    
    # Import routers here to avoid circular imports
    from app.api.routes.health import health_router
    from app.api.routes.metadata import metadata_router
    
    # Register routers with app instance
    app.include_router(
        health_router,
        prefix=f"{settings.API_V1_STR}/health",
        tags=["Health"]
    )
    
    app.include_router(
        metadata_router,
        prefix=f"{settings.API_V1_STR}/metadata",
        tags=["Metadata"]
    )
    
    # Add more routers here as they're implemented
    # TODO: Add product and inventory routers once implemented


app = create_application()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)