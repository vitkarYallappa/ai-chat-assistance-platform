from datetime import datetime
from typing import Dict, Optional, List, Any, Union
from uuid import UUID, uuid4
from enum import Enum

class MessageType(Enum):
    USER = "user"
    SYSTEM = "system"
    AI = "ai"

class Message:
    """
    Domain model representing a chat message in a conversation.
    Follows the Value Object pattern with immutable properties.
    """
    
    def __init__(
        self, 
        content: str,
        message_type: MessageType,
        conversation_id: UUID,
        user_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        embedding: Optional[List[float]] = None
    ):
        """
        Initialize a new message with content and metadata.
        
        Args:
            content: The text content of the message
            message_type: Type of message (user, system, or AI)
            conversation_id: ID of the conversation this message belongs to
            user_id: Optional ID of the user who sent the message
            tenant_id: Optional ID of the tenant this message belongs to
            metadata: Optional additional metadata for the message
            id: Optional UUID for the message (generated if not provided)
            created_at: Optional creation timestamp (current time if not provided)
            embedding: Optional vector embedding of the message content
        """
        self._id = id if id else uuid4()
        self._content = content
        self._message_type = message_type
        self._conversation_id = conversation_id
        self._user_id = user_id
        self._tenant_id = tenant_id
        self._metadata = metadata or {}
        self._created_at = created_at if created_at else datetime.utcnow()
        self._embedding = embedding
        
    @property
    def id(self) -> UUID:
        return self._id
        
    @property
    def content(self) -> str:
        return self._content
        
    @property
    def message_type(self) -> MessageType:
        return self._message_type
        
    @property
    def conversation_id(self) -> UUID:
        return self._conversation_id
        
    @property
    def user_id(self) -> Optional[UUID]:
        return self._user_id
        
    @property
    def tenant_id(self) -> Optional[UUID]:
        return self._tenant_id
        
    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata.copy()  # Return a copy to prevent modification
        
    @property
    def created_at(self) -> datetime:
        return self._created_at
        
    @property
    def embedding(self) -> Optional[List[float]]:
        return self._embedding
    
    def add_to_conversation(self, conversation: 'Conversation') -> 'Conversation':
        """
        Adds this message to a conversation and returns the updated conversation.
        This maintains immutability by returning a new conversation instance.
        
        Args:
            conversation: The conversation to add this message to
            
        Returns:
            A new conversation instance with this message added
        """
        if self._conversation_id != conversation.id:
            raise ValueError(f"Message conversation ID {self._conversation_id} does not match conversation {conversation.id}")
        
        return conversation.add_message(self)
    
    def to_embedding_input(self) -> str:
        """
        Prepares the message for embedding by formatting it into a standardized input.
        
        Returns:
            A formatted string suitable for embedding generation
        """
        prefix = f"{self._message_type.value}: "
        return prefix + self._content
    
    def get_token_count(self, tokenizer=None) -> int:
        """
        Calculates the token count for this message to manage context window limits.
        
        Args:
            tokenizer: Optional custom tokenizer to use (will use default if None)
            
        Returns:
            An estimated token count for this message
        """
        # Use a default simple tokenizer if none provided
        if tokenizer is None:
            # Rough estimate: ~4 chars per token for English text
            return len(self._content) // 4 + 5  # +5 for metadata overhead
        
        # Use the provided tokenizer
        return tokenizer.calculate_tokens(self._content)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Message):
            return False
        return self._id == other.id
    
    def __hash__(self) -> int:
        return hash(self._id)
    
    def __repr__(self) -> str:
        return f"Message(id={self._id}, type={self._message_type.value}, " \
               f"conversation_id={self._conversation_id}, created_at={self._created_at})"