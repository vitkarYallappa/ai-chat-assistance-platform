"""
API routers package for the MCP service.

This package contains FastAPI routers for different endpoints of the MCP service,
including health checks and webhook handlers.
"""

from app.api.routers.health import HealthRouter
from app.api.routers.webhooks import WebhookRouter

# Import router instances for use in main application
health_router = HealthRouter().router
webhook_router = WebhookRouter().router

__all__ = [
    # Router classes
    "HealthRouter",
    "WebhookRouter",
    
    # Router instances
    "health_router",
    "webhook_router",
]