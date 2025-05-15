"""
Domain layer package for the Chat Service.

This package contains the core domain models, interfaces, and schemas that define
the business logic and data structures of the Chat Service.
"""

from app.domain.models.conversation import Conversation

__all__ = [
    # Domain Models
    "Conversation",
]