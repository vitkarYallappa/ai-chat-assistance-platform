from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, validator

class MessageType(str, Enum):
    USER = "user"
    SYSTEM = "system"
    AI = "ai"

class MessageBase(BaseModel):
    """Base Pydantic schema for messages"""
    content: str = Field(..., description="The content of the message")
    message_type: MessageType = Field(..., description="The type of the message")
    
    class Config:
        use_enum_values = True

class MessageCreate(MessageBase):
    """Schema for creating messages"""
    conversation_id: UUID = Field(..., description="The ID of the conversation")
    user_id: Optional[UUID] = Field(None, description="The ID of the user who sent the message")
    tenant_id: Optional[UUID] = Field(None, description="The ID of the tenant")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('content')
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v

class MessageResponse(MessageBase):
    """Schema for message responses"""
    id: UUID = Field(..., description="The unique identifier of the message")
    conversation_id: UUID = Field(..., description="The ID of the conversation")
    user_id: Optional[UUID] = Field(None, description="The ID of the user who sent the message")
    tenant_id: Optional[UUID] = Field(None, description="The ID of the tenant")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="The timestamp of when the message was created")
    token_count: Optional[int] = Field(None, description="The token count of the message")
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "content": "Hello, how can I help you today?",
                "message_type": "ai",
                "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "user_id": None,
                "tenant_id": "3fa85f64-5717-4562-b3fc-2c963f66afb7",
                "metadata": {"model": "gpt-4", "prompt_tokens": 128},
                "created_at": "2023-01-01T00:00:00Z",
                "token_count": 10
            }
        }

class MessageListResponse(BaseModel):
    """Schema for message list responses"""
    items: List[MessageResponse] = Field(..., description="List of messages")
    total: int = Field(..., description="Total number of messages")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    
    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "content": "Hello, how can I help you today?",
                        "message_type": "ai",
                        "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "user_id": None,
                        "tenant_id": "3fa85f64-5717-4562-b3fc-2c963f66afb7",
                        "metadata": {"model": "gpt-4", "prompt_tokens": 128},
                        "created_at": "2023-01-01T00:00:00Z",
                        "token_count": 10
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10
            }
        }