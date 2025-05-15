"""
Message model representing a normalized message across all channels.

This module defines the core Message class that serves as the standardized internal
representation of messages, regardless of their source channel.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import validator


class Message:
    """
    Represents a normalized message in the system.
    
    A Message is the core domain model for all communication in the system.
    It contains the content of the message, metadata about the message,
    and information about the sender and recipient.
    """
    
    def __init__(
        self,
        message_id: Optional[str] = None,
        tenant_id: str = "",
        channel_id: str = "",
        conversation_id: Optional[str] = None,
        sender_id: str = "",
        recipient_id: str = "",
        message_type: str = "",
        content_type: str = "",
        content: Union[Dict[str, Any], str, bytes] = "",
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        channel_message_id: Optional[str] = None,
    ):
        """
        Initialize a new Message instance.
        
        Args:
            message_id: Unique identifier for the message (generated if not provided)
            tenant_id: Identifier of the tenant this message belongs to
            channel_id: Identifier of the channel this message was sent through
            conversation_id: Identifier of the conversation this message belongs to
            sender_id: Identifier of the message sender
            recipient_id: Identifier of the message recipient
            message_type: Type of message (text, image, audio, etc.)
            content_type: MIME type of the message content
            content: Actual message content (text, binary data, or structured content)
            metadata: Additional metadata associated with the message
            timestamp: When the message was created (defaults to current time)
            channel_message_id: Original message ID from the source channel
        """
        self.message_id = message_id or str(uuid4())
        self.tenant_id = tenant_id
        self.channel_id = channel_id
        self.conversation_id = conversation_id
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.message_type = message_type
        self.content_type = content_type
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.utcnow()
        self.channel_message_id = channel_message_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary representation.
        
        Returns:
            Dictionary representation of the message
        """
        return {
            "message_id": self.message_id,
            "tenant_id": self.tenant_id,
            "channel_id": self.channel_id,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "message_type": self.message_type,
            "content_type": self.content_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "channel_message_id": self.channel_message_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """
        Create a message from a dictionary representation.
        
        Args:
            data: Dictionary representation of a message
            
        Returns:
            A new Message instance
        """
        # Handle timestamp conversion if it's a string
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        
        return cls(**data)
    
    def validate(self) -> bool:
        """
        Validate the message structure and content.
        
        Returns:
            True if the message is valid, False otherwise
            
        Raises:
            ValidationException: If the message is invalid with detailed validation errors
        """
        errors = []
        
        # Check required fields
        if not self.tenant_id:
            errors.append("tenant_id is required")
        
        if not self.channel_id:
            errors.append("channel_id is required")
        
        if not self.message_type:
            errors.append("message_type is required")
        
        if not self.content_type:
            errors.append("content_type is required")
        
        # Validate content based on message_type and content_type
        if self.message_type == "text":
            if self.content_type != "text/plain":
                errors.append(f"Invalid content_type '{self.content_type}' for text message")
            
            if not isinstance(self.content, str):
                errors.append("Content for text message must be a string")
        
        elif self.message_type == "image":
            if not self.content_type.startswith("image/"):
                errors.append(f"Invalid content_type '{self.content_type}' for image message")
        
        # Additional validations can be added for other message types
        
        if errors:
            from app.utils.exceptions import ValidationException
            raise ValidationException(f"Message validation failed: {'; '.join(errors)}")
        
        return True
    
    def __repr__(self) -> str:
        """String representation of the message for debugging."""
        return (f"Message(message_id={self.message_id}, "
                f"tenant_id={self.tenant_id}, "
                f"channel_id={self.channel_id}, "
                f"message_type={self.message_type}, "
                f"timestamp={self.timestamp})")