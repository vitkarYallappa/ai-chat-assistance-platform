"""
API layer package for the Chat Service.

This package contains the API layer components including FastAPI dependencies,
routers, and error handlers for the Chat Service.
"""

from app.api.dependencies import (
    get_conversation_service,
    get_message_service,
    get_intent_service,
    get_current_tenant,
    get_vector_search_service
)

__all__ = [
    # Dependencies
    "get_conversation_service",
    "get_message_service",
    "get_intent_service",
    "get_current_tenant",
    "get_vector_search_service",
]