from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import uuid
from enum import Enum
from pydantic import BaseModel, Field

from app.utils.exceptions import ValidationException


class MessageRole(str, Enum):
    """Enumeration of possible message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ContentType(str, Enum):
    """Enumeration of supported content types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    LOCATION = "location"
    INTERACTIVE = "interactive"


class Message:
    """Domain model for a message within a conversation."""
    
    def __init__(
        self,
        content: str,
        role: MessageRole = MessageRole.USER,
        content_type: ContentType = ContentType.TEXT,
        id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a message.
        
        Args:
            content: Message content
            role: Role of the message sender
            content_type: Type of content in the message
            id: Unique identifier (generated if not provided)
            created_at: Creation timestamp (current time if not provided)
            metadata: Additional message metadata
        """
        self.id = id or uuid.uuid4()
        self.content = content
        self.role = role if isinstance(role, MessageRole) else MessageRole(role)
        self.content_type = content_type if isinstance(content_type, ContentType) else ContentType(content_type)
        self.created_at = created_at or datetime.utcnow()
        self.metadata = metadata or {}
        
        self._validate()
    
    def _validate(self) -> None:
        """
        Validate message data.
        
        Raises:
            ValidationException: If validation fails
        """
        if not self.content.strip():
            raise ValidationException(
                message="Message content cannot be empty",
                details={"field": "content"}
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert message to dictionary representation.
        
        Returns:
            Dict: Dictionary representation of the message
        """
        return {
            "id": str(self.id),
            "content": self.content,
            "role": self.role.value,
            "content_type": self.content_type.value,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """
        Create message from dictionary representation.
        
        Args:
            data: Dictionary representation of the message
            
        Returns:
            Message: Message instance
        """
        message_id = data.get("id")
        if message_id and isinstance(message_id, str):
            message_id = uuid.UUID(message_id)
            
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            id=message_id,
            content=data["content"],
            role=data["role"],
            content_type=data.get("content_type", ContentType.TEXT),
            created_at=created_at,
            metadata=data.get("metadata", {})
        )


class Conversation:
    """Domain model for a conversation."""
    
    def __init__(
        self,
        id: Optional[uuid.UUID] = None,
        title: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        messages: Optional[List[Message]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_archived: bool = False,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Initialize a conversation.
        
        Args:
            id: Unique identifier (generated if not provided)
            title: Conversation title
            created_at: Creation timestamp (current time if not provided)
            updated_at: Last update timestamp (current time if not provided)
            messages: List of messages in the conversation
            metadata: Additional conversation metadata
            is_archived: Whether the conversation is archived
            tenant_id: ID of the tenant that owns this conversation
            user_id: ID of the user that owns this conversation
        """
        self.id = id or uuid.uuid4()
        self.title = title
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at
        self.messages = messages or []
        self.metadata = metadata or {}
        self.is_archived = is_archived
        self.tenant_id = tenant_id
        self.user_id = user_id
        
        # Internal state
        self._context: Dict[str, Any] = {}
        self._intents: Set[str] = set()
    
    def add_message(self, message: Message) -> None:
        """
        Add a message to the conversation.
        
        Args:
            message: Message to add
        """
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
    
    def set_context(self, context: Dict[str, Any]) -> None:
        """
        Update the conversation context.
        
        Args:
            context: New context data to set
        """
        self._context.update(context)
        self.updated_at = datetime.utcnow()
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get the current conversation context.
        
        Returns:
            Dict: Current context data
        """
        return self._context.copy()
    
    def add_intent(self, intent: str) -> None:
        """
        Add a detected intent to the conversation.
        
        Args:
            intent: Intent identifier
        """
        self._intents.add(intent)
    
    def has_intent(self, intent: str) -> bool:
        """
        Check if an intent has been detected in this conversation.
        
        Args:
            intent: Intent identifier to check
            
        Returns:
            bool: True if the intent has been detected
        """
        return intent in self._intents
    
    def get_intents(self) -> Set[str]:
        """
        Get all detected intents in this conversation.
        
        Returns:
            Set[str]: Set of detected intents
        """
        return self._intents.copy()
    
    def archive(self) -> None:
        """Mark the conversation as archived."""
        self.is_archived = True
        self.updated_at = datetime.utcnow()
    
    def unarchive(self) -> None:
        """Mark the conversation as not archived."""
        self.is_archived = False
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert conversation to dictionary representation.
        
        Returns:
            Dict: Dictionary representation of the conversation
        """
        return {
            "id": str(self.id),
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [msg.to_dict() for msg in self.messages],
            "metadata": self.metadata,
            "is_archived": self.is_archived,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "_context": self._context,
            "_intents": list(self._intents)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """
        Create conversation from dictionary representation.
        
        Args:
            data: Dictionary representation of the conversation
            
        Returns:
            Conversation: Conversation instance
        """
        conversation_id = data.get("id")
        if conversation_id and isinstance(conversation_id, str):
            conversation_id = uuid.UUID(conversation_id)
            
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
            
        updated_at = data.get("updated_at")
        if updated_at and isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        messages = []
        for msg_data in data.get("messages", []):
            messages.append(Message.from_dict(msg_data))
        
        conversation = cls(
            id=conversation_id,
            title=data.get("title"),
            created_at=created_at,
            updated_at=updated_at,
            messages=messages,
            metadata=data.get("metadata", {}),
            is_archived=data.get("is_archived", False),
            tenant_id=data.get("tenant_id"),
            user_id=data.get("user_id")
        )
        
        # Add internal state
        context = data.get("_context", {})
        if context:
            conversation.set_context(context)
            
        intents = data.get("_intents", [])
        for intent in intents:
            conversation.add_intent(intent)
        
        return conversation