"""
Message schemas for API request and response validation.

This module defines Pydantic schemas for validating message-related API
requests and responses, ensuring consistent data structures.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class MessageType(str, Enum):
    """Enumeration of supported message types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    LOCATION = "location"
    CONTACT = "contact"
    INTERACTIVE = "interactive"
    TEMPLATE = "template"
    UNKNOWN = "unknown"


class ContentType(str, Enum):
    """Enumeration of supported content types."""
    TEXT_PLAIN = "text/plain"
    IMAGE_JPEG = "image/jpeg"
    IMAGE_PNG = "image/png"
    IMAGE_GIF = "image/gif"
    AUDIO_MP3 = "audio/mp3"
    AUDIO_OGG = "audio/ogg"
    VIDEO_MP4 = "video/mp4"
    DOCUMENT_PDF = "application/pdf"
    DOCUMENT_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    APPLICATION_JSON = "application/json"
    UNKNOWN = "unknown"


class MessageBase(BaseModel):
    """Base schema for all message-related schemas."""
    
    tenant_id: str = Field(..., description="Identifier of the tenant")
    channel_id: str = Field(..., description="Identifier of the channel")
    message_type: MessageType = Field(..., description="Type of message")
    content_type: ContentType = Field(..., description="MIME type of the content")
    sender_id: Optional[str] = Field(None, description="Identifier of the sender")
    recipient_id: Optional[str] = Field(None, description="Identifier of the recipient")
    conversation_id: Optional[str] = Field(None, description="Identifier of the conversation")
    
    class Config:
        use_enum_values = True


class MessageContent(BaseModel):
    """Schema for message content."""
    
    content: Union[str, Dict[str, Any], bytes] = Field(
        ..., description="The actual content of the message"
    )
    
    @validator("content")
    def validate_content(cls, v, values):
        """Validate content based on message_type and content_type."""
        message_type = values.get("message_type")
        content_type = values.get("content_type")
        
        if message_type == MessageType.TEXT:
            if content_type != ContentType.TEXT_PLAIN:
                raise ValueError(f"Invalid content_type for text message: {content_type}")
            
            if not isinstance(v, str):
                raise ValueError("Content for text message must be a string")
        
        elif message_type == MessageType.IMAGE:
            if not content_type.startswith("image/"):
                raise ValueError(f"Invalid content_type for image message: {content_type}")
        
        # Additional validations can be added for other message types
        
        return v


class MessageCreate(MessageBase, MessageContent):
    """Schema for creating a new message."""
    
    metadata: Optional[Dict[str, Any]] = Field(
        default={}, description="Additional metadata for the message"
    )


class MessageResponse(MessageBase, MessageContent):
    """Schema for message responses."""
    
    message_id: str = Field(..., description="Unique identifier for the message")
    timestamp: datetime = Field(..., description="When the message was created")
    metadata: Dict[str, Any] = Field(
        default={}, description="Additional metadata for the message"
    )
    channel_message_id: Optional[str] = Field(
        None, description="Original message ID from the source channel"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class MessageDeliveryStatus(BaseModel):
    """Schema for message delivery status updates."""
    
    message_id: str = Field(..., description="Identifier of the message")
    channel_message_id: Optional[str] = Field(
        None, description="Channel-specific message ID"
    )
    status: str = Field(..., description="Delivery status (sent, delivered, read, failed)")
    timestamp: datetime = Field(..., description="When the status was updated")
    error: Optional[str] = Field(None, description="Error message if status is 'failed'")
    metadata: Optional[Dict[str, Any]] = Field(
        default={}, description="Additional metadata for the delivery status"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class MessageQuery(BaseModel):
    """Schema for querying messages."""
    
    tenant_id: str = Field(..., description="Identifier of the tenant")
    conversation_id: Optional[str] = Field(None, description="Filter by conversation ID")
    sender_id: Optional[str] = Field(None, description="Filter by sender ID")
    recipient_id: Optional[str] = Field(None, description="Filter by recipient ID")
    channel_id: Optional[str] = Field(None, description="Filter by channel ID")
    message_type: Optional[MessageType] = Field(None, description="Filter by message type")
    start_time: Optional[datetime] = Field(None, description="Filter by start time")
    end_time: Optional[datetime] = Field(None, description="Filter by end time")
    limit: int = Field(50, description="Maximum number of messages to return")
    offset: int = Field(0, description="Number of messages to skip")
    
    class Config:
        use_enum_values = True