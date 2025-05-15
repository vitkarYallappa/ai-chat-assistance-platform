from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import time
import uuid
from typing import List, Callable

from app.config import get_settings
from app.api.routers import health, webhooks
from app.api.error_handlers import setup_exception_handlers
from app.api.websocket.connection_manager import ConnectionManager
from app.utils.logger import setup_logging

# Creating a lifespan context to handle startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    setup_logging(settings.logging.LEVEL, settings.logging.FORMAT)
    logging.info(f"Starting {settings.APP_NAME} in {settings.ENV} mode")
    
    # Initialize connection manager as a singleton
    app.state.connection_manager = ConnectionManager()
    
    # Startup additional services or connections here
    # ...
    
    yield
    
    # Shutdown
    logging.info(f"Shutting down {settings.APP_NAME}")
    
    # Close any connections or resources
    # ...

def create_application() -> FastAPI:
    """
    Creates and configures the FastAPI application.
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.APP_NAME,
        description="Message Control Processor (MCP) Service for the AI Chat Assistance Platform",
        version="0.1.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # Add middlewares
    configure_middleware(app)
    
    # Register routers
    register_routers(app)
    
    # Configure exception handlers
    setup_exception_handlers(app)
    
    # Configure WebSocket
    configure_websocket(app)
    
    return app

def configure_middleware(app: FastAPI) -> None:
    """
    Configure middleware components for the application.
    """
    settings = get_settings()
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Correlation ID middleware
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next: Callable):
        # Generate or extract correlation ID
        correlation_id = request.headers.get(
            settings.logging.CORRELATION_ID_HEADER, 
            str(uuid.uuid4())
        )
        
        # Add correlation ID to request state
        request.state.correlation_id = correlation_id
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add correlation ID to response headers
        response.headers[settings.logging.CORRELATION_ID_HEADER] = correlation_id
        
        # Log request details
        logging.info(
            f"Request processed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "processing_time": process_time,
                "status_code": response.status_code
            }
        )
        
        return response
    
    # Tenant context middleware
    @app.middleware("http")
    async def tenant_context_middleware(request: Request, call_next: Callable):
        # Extract tenant ID from request
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            request.state.tenant_id = tenant_id
        
        return await call_next(request)

def register_routers(app: FastAPI) -> None:
    """
    Register API routers with the application.
    """
    settings = get_settings()
    
    # Include routers with prefix
    app.include_router(
        health.router,
        prefix=f"{settings.API_PREFIX}/health",
        tags=["health"]
    )
    
    app.include_router(
        webhooks.router,
        prefix=f"{settings.API_PREFIX}/webhooks",
        tags=["webhooks"]
    )
    
    # Add more routers here as they are implemented
    # ...

def configure_websocket(app: FastAPI) -> None:
    """
    Configure WebSocket server components.
    """
    # WebSocket endpoint will be configured in a separate module
    # and registered here with the app
    from app.api.websocket.server import router as websocket_router
    app.include_router(websocket_router)

app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=get_settings().DEBUG,
        log_level=get_settings().logging.LEVEL.lower()
    )