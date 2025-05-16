"""
Service responsible for managing conversations in the Chat Service.

This service handles conversation lifecycles, including creation, retrieval,
and updating of conversations. It also manages conversation context and builds
context windows for AI model interactions.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from app.domain.models.conversation import Conversation
from app.domain.models.message import Message
from app.infrastructure.repositories.conversation_repository import ConversationRepository
from app.utils.logger import get_logger
from app.utils.exceptions import ConversationNotFoundError, RepositoryError


class ConversationService:
    """
    Service responsible for managing conversations, including creation,
    retrieval, and context management.
    """
    
    def __init__(self, conversation_repository: ConversationRepository):
        """
        Initialize the conversation service with dependencies.
        
        Args:
            conversation_repository: Repository for conversation storage
        """
        self.repository = conversation_repository
        self.logger = get_logger(__name__)
    
    async def create_conversation(
        self, 
        tenant_id: str, 
        user_id: str, 
        channel_id: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            tenant_id: ID of the tenant
            user_id: ID of the user
            channel_id: ID of the channel
            metadata: Optional metadata for the conversation
            
        Returns:
            The created conversation
            
        Raises:
            RepositoryError: If the conversation could not be created
        """
        try:
            conversation_id = str(uuid.uuid4())
            
            conversation = Conversation(
                id=conversation_id,
                tenant_id=tenant_id,
                user_id=user_id,
                channel_id=channel_id,
                started_at=datetime.now(),
                last_updated_at=datetime.now(),
                status="active",
                metadata=metadata or {},
                context={},
                messages=[]
            )
            
            self.logger.info(f"Creating new conversation: {conversation_id}")
            
            # Save the conversation
            saved_conversation = await self.repository.create(conversation)
            
            self.logger.debug(f"Created conversation: {conversation_id}")
            
            return saved_conversation
            
        except Exception as e:
            self.logger.error(f"Failed to create conversation: {str(e)}", exc_info=True)
            raise RepositoryError(f"Failed to create conversation: {str(e)}")
    
    async def get_conversation(self, conversation_id: str) -> Conversation:
        """
        Get a conversation by ID.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            The conversation
            
        Raises:
            ConversationNotFoundError: If the conversation is not found
            RepositoryError: If the conversation could not be retrieved
        """
        try:
            self.logger.debug(f"Getting conversation: {conversation_id}")
            
            conversation = await self.repository.get_by_id(conversation_id)
            
            if not conversation:
                raise ConversationNotFoundError(f"Conversation not found: {conversation_id}")
                
            return conversation
            
        except ConversationNotFoundError as e:
            self.logger.warning(str(e))
            raise
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation: {str(e)}", exc_info=True)
            raise RepositoryError(f"Failed to get conversation: {str(e)}")
    
    async def add_message(self, conversation_id: str, message: Message) -> Conversation:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            message: Message to add
            
        Returns:
            The updated conversation
            
        Raises:
            ConversationNotFoundError: If the conversation is not found
            RepositoryError: If the message could not be added
        """
        try:
            self.logger.debug(f"Adding message to conversation: {conversation_id}")
            
            # Get the conversation
            conversation = await self.get_conversation(conversation_id)
            
            # Add the message to the conversation
            conversation.messages.append(message)
            
            # Update the last updated timestamp
            conversation.last_updated_at = datetime.now()
            
            # Save the updated conversation
            updated_conversation = await self.repository.update(conversation)
            
            self.logger.debug(f"Added message to conversation: {conversation_id}")
            
            return updated_conversation
            
        except ConversationNotFoundError:
            raise
            
        except Exception as e:
            self.logger.error(f"Failed to add message to conversation: {str(e)}", exc_info=True)
            raise RepositoryError(f"Failed to add message to conversation: {str(e)}")
    
    async def update_context(
        self, 
        conversation_id: str, 
        context_updates: Dict[str, Any]
    ) -> Conversation:
        """
        Update the context of a conversation.
        
        Args:
            conversation_id: ID of the conversation
            context_updates: Updates to the context
            
        Returns:
            The updated conversation
            
        Raises:
            ConversationNotFoundError: If the conversation is not found
            RepositoryError: If the context could not be updated
        """
        try:
            self.logger.debug(f"Updating context for conversation: {conversation_id}")
            
            # Get the conversation
            conversation = await self.get_conversation(conversation_id)
            
            # Update the context
            conversation.context.update(context_updates)
            
            # Update the last updated timestamp
            conversation.last_updated_at = datetime.now()
            
            # Save the updated conversation
            updated_conversation = await self.repository.update(conversation)
            
            self.logger.debug(f"Updated context for conversation: {conversation_id}")
            
            return updated_conversation
            
        except ConversationNotFoundError:
            raise
            
        except Exception as e:
            self.logger.error(f"Failed to update context for conversation: {str(e)}", exc_info=True)
            raise RepositoryError(f"Failed to update context for conversation: {str(e)}")
    
    def build_conversation_context(
        self, 
        conversation: Conversation, 
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Build a context window for a conversation, suitable for AI models.
        
        Args:
            conversation: The conversation to build context for
            max_tokens: Maximum number of tokens for the context
            
        Returns:
            The context window
        """
        try:
            self.logger.debug(f"Building context for conversation: {conversation.id}")
            
            # Start with the base context
            context = {
                "conversation_id": conversation.id,
                "user_id": conversation.user_id,
                "tenant_id": conversation.tenant_id,
                "channel_id": conversation.channel_id,
                "custom_context": conversation.context,
            }
            
            # Get the most recent messages that fit within the token limit
            messages = []
            current_tokens = self._estimate_token_count(context)
            
            # Process messages in reverse order (newest first)
            for message in reversed(conversation.messages):
                message_tokens = self._estimate_token_count(message.content)
                
                if current_tokens + message_tokens <= max_tokens:
                    messages.insert(0, {
                        "role": "user" if message.sender_id == conversation.user_id else "assistant",
                        "content": message.content,
                        "timestamp": message.timestamp.isoformat()
                    })
                    current_tokens += message_tokens
                else:
                    # If we can't fit any more messages, stop
                    break
            
            context["messages"] = messages
            
            self.logger.debug(f"Built context for conversation: {conversation.id}, tokens: {current_tokens}")
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to build context for conversation: {str(e)}", exc_info=True)
            # Return a minimal context in case of error
            return {
                "conversation_id": conversation.id,
                "messages": []
            }
    
    def _estimate_token_count(self, text: Any) -> int:
        """
        Estimate the number of tokens in a text.
        
        Args:
            text: The text to estimate tokens for
            
        Returns:
            An estimate of the number of tokens
        """
        # A simple estimation: 1 token is about 4 characters for English text
        if isinstance(text, str):
            return len(text) // 4 + 1
            
        # For dictionaries or other objects, use their string representation
        return len(str(text)) // 4 + 1