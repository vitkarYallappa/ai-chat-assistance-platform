"""
API routers package for the Chat Service.

This package contains FastAPI routers for different endpoints of the Chat Service,
including health checks and conversation management.
"""

from app.api.routers.health import HealthRouter
from app.api.routers.conversations import ConversationRouter

# Import router instances for use in main application
health_router = HealthRouter().router
conversation_router = ConversationRouter().router

__all__ = [
    # Router classes
    "HealthRouter",
    "ConversationRouter",
    
    # Router instances
    "health_router",
    "conversation_router",
]