"""
Schema package for Pydantic models used in API request/response validation.
This file exports all schema classes for easier importing elsewhere.
"""

# Message schemas
from app.domain.schemas.message import (
    MessageType,
    MessageBase,
    MessageCreate,
    MessageResponse,
    MessageListResponse
)

# Conversation schemas
from app.domain.schemas.conversation import (
    ConversationStatus,
    ConversationBase,
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse
)

# Export all for easy importing
__all__ = [
    # Message types
    "MessageType",
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    "MessageListResponse",
    
    # Conversation types
    "ConversationStatus",
    "ConversationBase",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationListResponse"
]