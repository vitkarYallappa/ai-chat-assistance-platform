"""
Service responsible for managing conversation context in the Chat Service.

This service handles building and managing conversation context windows,
pruning context to fit token limits, prioritizing messages for context,
calculating token usage, and extracting relevant entities from context.
"""

from typing import Dict, List, Optional, Any
import json

from app.domain.models.conversation import Conversation
from app.domain.models.message import Message
from app.infrastructure.ai.embeddings.embedding_service import EmbeddingService
from app.utils.logger import get_logger
from app.utils.exceptions import ContextBuildingError


class ContextService:
    """
    Service responsible for managing conversation context, including
    building context windows, pruning context, and token management.
    """
    
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Initialize the context service with dependencies.
        
        Args:
            embedding_service: Optional service for text embeddings
        """
        self.embedding_service = embedding_service
        self.logger = get_logger(__name__)
    
    async def build_context(
        self,
        conversation: Conversation,
        current_message: Message,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Build a context window for a conversation.
        
        Args:
            conversation: The conversation to build context for
            current_message: The current message being processed
            max_tokens: Maximum number of tokens for the context
            
        Returns:
            The context window
            
        Raises:
            ContextBuildingError: If the context could not be built
        """
        try:
            self.logger.info(f"Building context for conversation: {conversation.id}")
            
            # Start with system context
            context = {
                "system": {
                    "conversation_id": conversation.id,
                    "tenant_id": conversation.tenant_id,
                    "user_id": conversation.user_id,
                    "channel_id": conversation.channel_id
                },
                "custom_context": conversation.context or {},
                "messages": []
            }
            
            # Calculate current token usage
            current_tokens = self.calculate_tokens(context)
            max_message_tokens = max_tokens - current_tokens
            
            # Get messages for context
            if conversation.messages:
                # Prioritize messages
                prioritized_messages = self.prioritize_messages(
                    messages=conversation.messages,
                    current_message=current_message
                )
                
                # Add messages to context
                context["messages"] = self.prune_context(
                    messages=prioritized_messages,
                    max_tokens=max_message_tokens
                )
            
            # Add entities
            entities = await self.extract_entities(
                messages=context["messages"],
                conversation_context=conversation.context
            )
            
            if entities:
                context["entities"] = entities
            
            # Update token count
            final_token_count = self.calculate_tokens(context)
            context["token_count"] = final_token_count
            
            self.logger.info(f"Built context for conversation: {conversation.id}, tokens: {final_token_count}")
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to build context: {str(e)}", exc_info=True)
            raise ContextBuildingError(f"Failed to build context: {str(e)}")
    
    def prune_context(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int
    ) -> List[Dict[str, Any]]:
        """
        Prune messages to fit within token limits.
        
        Args:
            messages: The messages to prune
            max_tokens: Maximum number of tokens
            
        Returns:
            Pruned messages that fit within the token limit
        """
        pruned_messages = []
        current_tokens = 0
        
        for message in messages:
            message_tokens = self.calculate_tokens(message)
            
            if current_tokens + message_tokens <= max_tokens:
                pruned_messages.append(message)
                current_tokens += message_tokens
            else:
                self.logger.debug(f"Pruning message: {message.get('id')}, would exceed token limit")
                # Stop adding messages once we reach the limit
                break
        
        self.logger.debug(f"Pruned context to {len(pruned_messages)} messages, {current_tokens} tokens")
        
        return pruned_messages
    
    def prioritize_messages(
        self,
        messages: List[Message],
        current_message: Message
    ) -> List[Dict[str, Any]]:
        """
        Prioritize messages for inclusion in context.
        
        Args:
            messages: All messages in the conversation
            current_message: The current message being processed
            
        Returns:
            Prioritized messages for context
        """
        # Convert domain models to dictionaries
        message_dicts = []
        
        for msg in messages:
            message_dicts.append({
                "id": msg.id,
                "role": "user" if msg.sender_id == current_message.sender_id else "assistant",
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "relevance": 1.0  # Default relevance
            })
        
        # Sort by recency (most recent first)
        message_dicts.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # If we have an embedding service, calculate relevance to current message
        if self.embedding_service:
            try:
                # Calculate embeddings for all messages
                current_embedding = self.embedding_service.embed_text(current_message.content)
                
                # Update relevance scores based on similarity to current message
                for msg in message_dicts:
                    msg_embedding = self.embedding_service.embed_text(msg["content"])
                    similarity = self.embedding_service.cosine_similarity(current_embedding, msg_embedding)
                    msg["relevance"] = similarity
                
                # Re-sort by a combination of recency and relevance
                message_dicts.sort(key=lambda x: (0.7 * x["relevance"] + 0.3 * (1.0 if x["timestamp"] > "2023-01-01" else 0.0)), reverse=True)
                
            except Exception as e:
                self.logger.warning(f"Failed to calculate relevance: {str(e)}")
                # Fall back to recency-based sorting
                pass
        
        # Add a priority field based on the sorted order
        for i, msg in enumerate(message_dicts):
            msg["priority"] = len(message_dicts) - i
        
        return message_dicts
    
    def calculate_tokens(self, obj: Any) -> int:
        """
        Calculate the number of tokens in an object.
        
        Args:
            obj: The object to calculate tokens for
            
        Returns:
            Number of tokens
        """
        if isinstance(obj, str):
            # Estimate: 1 token is roughly 4 characters for English text
            return len(obj) // 4 + 1
            
        elif isinstance(obj, dict):
            # Sum tokens for keys and values
            return sum(self.calculate_tokens(k) + self.calculate_tokens(v) for k, v in obj.items())
            
        elif isinstance(obj, list):
            # Sum tokens for list items
            return sum(self.calculate_tokens(item) for item in obj)
            
        elif obj is None:
            return 0
            
        else:
            # Convert to string for other types
            return len(str(obj)) // 4 + 1
    
    async def extract_entities(
        self,
        messages: List[Dict[str, Any]],
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract entities from context.
        
        Args:
            messages: Messages to extract entities from
            conversation_context: Additional conversation context
            
        Returns:
            Extracted entities
        """
        entities = {}
        
        try:
            # First, check if entities are already in the conversation context
            if conversation_context and "entities" in conversation_context:
                entities.update(conversation_context["entities"])
            
            # Extract entities from messages
            for message in messages:
                if "entities" in message:
                    entities.update(message["entities"])
                    continue
                
                # Use NER or pattern matching to extract entities
                # This is a simplified example
                content = message["content"]
                
                # Example: Extract email addresses
                import re
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, content)
                
                if emails:
                    entities["email"] = emails[0]  # Take the first email
                
                # More entity extraction could be added here
            
            return entities
            
        except Exception as e:
            self.logger.warning(f"Failed to extract entities: {str(e)}")
            return entities