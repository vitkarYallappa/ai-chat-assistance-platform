from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator

class ConversationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"

class ConversationBase(BaseModel):
    """Base Pydantic schema for conversations"""
    title: Optional[str] = Field(None, description="The title of the conversation")
    
    class Config:
        use_enum_values = True

class ConversationCreate(ConversationBase):
    """Schema for creating conversations"""
    user_id: Optional[UUID] = Field(None, description="The ID of the user")
    tenant_id: UUID = Field(..., description="The ID of the tenant")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('tenant_id')
    def tenant_id_required(cls, v):
        if v is None:
            raise ValueError('Tenant ID is required')
        return v

class ConversationUpdate(BaseModel):
    """Schema for updating conversations"""
    title: Optional[str] = Field(None, description="The title of the conversation")
    status: Optional[ConversationStatus] = Field(None, description="The status of the conversation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class ConversationResponse(ConversationBase):
    """Schema for conversation responses"""
    id: UUID = Field(..., description="The unique identifier of the conversation")
    user_id: Optional[UUID] = Field(None, description="The ID of the user")
    tenant_id: UUID = Field(..., description="The ID of the tenant")
    status: ConversationStatus = Field(..., description="The status of the conversation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="The timestamp of when the conversation was created")
    updated_at: datetime = Field(..., description="The timestamp of when the conversation was last updated")
    message_count: int = Field(..., description="The number of messages in the conversation")
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "title": "Product Inquiry",
                "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
                "tenant_id": "3fa85f64-5717-4562-b3fc-2c963f66afb7",
                "status": "active",
                "metadata": {"source": "web", "channel": "chat"},
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:10:00Z",
                "message_count": 5
            }
        }

class ConversationListResponse(BaseModel):
    """Schema for conversation list responses"""
    items: List[ConversationResponse] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    
    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "title": "Product Inquiry",
                        "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
                        "tenant_id": "3fa85f64-5717-4562-b3fc-2c963f66afb7",
                        "status": "active",
                        "metadata": {"source": "web", "channel": "chat"},
                        "created_at": "2023-01-01T00:00:00Z",
                        "updated_at": "2023-01-01T00:10:00Z",
                        "message_count": 5
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10
            }
        }