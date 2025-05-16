
"""
Domain models for the Chat Service.

This package contains the core domain models that represent the business entities
in the Chat Service domain, such as conversations, messages, and intents.
"""

from app.domain.models.conversation import Conversation

__all__ = [
    "Conversation",
]