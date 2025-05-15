"""
Domain schemas for the MCP service.

This package contains the Pydantic schemas used for validating input and output
data in the MCP service API layer.
"""

from app.domain.schemas.message import (
    MessageBase,
    MessageContent,
    MessageCreate,
    MessageResponse,
    MessageDeliveryStatus,
    MessageQuery,
    MessageType,
    ContentType
)

__all__ = [
    "MessageBase",
    "MessageContent",
    "MessageCreate",
    "MessageResponse",
    "MessageDeliveryStatus",
    "MessageQuery",
    "MessageType",
    "ContentType",
]