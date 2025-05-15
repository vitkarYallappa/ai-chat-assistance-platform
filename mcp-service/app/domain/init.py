"""
Domain layer package for the MCP service.

This package contains the core domain models, interfaces, and schemas that define
the business logic and data structures of the MCP service.
"""

from app.domain.models.message import Message
from app.domain.models.channel import Channel
from app.domain.interfaces.channel_interface import ChannelInterface
from app.domain.interfaces.normalizer_interface import NormalizerInterface
from app.domain.schemas.message import (
    MessageBase,
    MessageCreate,
    MessageResponse,
    MessageDeliveryStatus,
    MessageQuery,
    MessageType,
    ContentType
)

__all__ = [
    # Domain Models
    "Message",
    "Channel",
    
    # Domain Interfaces
    "ChannelInterface",
    "NormalizerInterface",
    
    # Domain Schemas
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    "MessageDeliveryStatus",
    "MessageQuery",
    "MessageType",
    "ContentType",
]