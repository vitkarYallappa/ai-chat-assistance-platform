from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
from contextlib import asynccontextmanager

from app.config import get_settings
from app.utils.logger import configure_logging, get_logger
from app.utils.exceptions import AppException
from app.api.routers import health, conversations


# Configure logging
configure_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.
    
    Args:
        app: FastAPI application instance
    """
    # Startup operations
    logger.info(f"Starting {settings.SERVICE_NAME} service")
    
    # TODO: Initialize database connections
    # TODO: Initialize cache clients
    # TODO: Initialize external service clients
    
    yield
    
    # Shutdown operations
    logger.info(f"Shutting down {settings.SERVICE_NAME} service")
    
    # TODO: Close database connections
    # TODO: Close cache clients
    # TODO: Close external service clients


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title=f"{settings.SERVICE_NAME.capitalize()} API",
        description="Chat Service API for AI Chat Assistance Platform",
        version=settings.VERSION,
        lifespan=lifespan,
        debug=settings.DEBUG
    )
    
    configure_middleware(app)
    register_routers(app)
    configure_exception_handlers(app)
    
    return app


def configure_middleware(app: FastAPI) -> None:
    """
    Configure middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure this for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Correlation ID middleware
    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


def register_routers(app: FastAPI) -> None:
    """
    Register API routers with the application.
    
    Args:
        app: FastAPI application instance
    """
    app.include_router(health.router, tags=["Health"])
    app.include_router(
        conversations.router,
        prefix=f"{settings.API_PREFIX}/conversations",
        tags=["Conversations"]
    )


def configure_exception_handlers(app: FastAPI) -> None:
    """
    Configure global exception handlers.
    
    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException):
        logger.error(
            f"Application exception: {exc.message}",
            extra={
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "details": exc.details,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception):
        logger.exception(
            f"Unhandled exception: {str(exc)}",
            extra={"path": request.url.path}
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "message": str(exc) if settings.DEBUG else "An unexpected error occurred",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        )


# Create application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )