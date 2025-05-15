"""
API package for the MCP service.

This package contains the API layer components including FastAPI dependencies,
routers, error handlers, and WebSocket implementations.
"""

from app.api.dependencies import (
    get_channel_factory,
    get_tenant_repository,
    get_message_service,
    get_current_tenant
)

from app.api.error_handlers import (
    handle_api_exception,
    handle_validation_exception,
    handle_channel_exception
)

__all__ = [
    # Dependencies
    "get_channel_factory",
    "get_tenant_repository",
    "get_message_service",
    "get_current_tenant",
    
    # Error handlers
    "handle_api_exception",
    "handle_validation_exception",
    "handle_channel_exception",
]