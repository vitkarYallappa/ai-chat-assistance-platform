"""
Service responsible for processing messages in the Chat Service.

This service handles the processing of incoming and outgoing messages,
including creation, formatting, and storage of messages. It also tracks
message metrics for monitoring and analytics.
"""

from typing import Dict, Optional, Any
from datetime import datetime
import uuid

from app.domain.models.message import Message
from app.domain.models.conversation import Conversation
from app.infrastructure.repositories.message_repository import MessageRepository
from app.domain.services.conversation_service import ConversationService
from app.utils.logger import get_logger
from app.utils.exceptions import MessageNotFoundError, RepositoryError, ProcessingError
from app.utils.metrics import MetricsCollector


class MessageService:
    """
    Service responsible for processing messages, including creation,
    formatting, and storage.
    """
    
    def __init__(
        self, 
        message_repository: MessageRepository,
        conversation_service: ConversationService,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        """
        Initialize the message service with dependencies.
        
        Args:
            message_repository: Repository for message storage
            conversation_service: Service for conversation management
            metrics_collector: Optional collector for metrics
        """
        self.repository = message_repository
        self.conversation_service = conversation_service
        self.metrics = metrics_collector
        self.logger = get_logger(__name__)
    
    async def process_message(
        self, 
        content: str,
        conversation_id: str,
        tenant_id: str,
        user_id: str,
        channel_id: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an incoming message.
        
        Args:
            content: Content of the message
            conversation_id: ID of the conversation
            tenant_id: ID of the tenant
            user_id: ID of the user
            channel_id: ID of the channel
            message_type: Type of the message
            metadata: Optional metadata for the message
            
        Returns:
            Response data including the processed message and response
            
        Raises:
            ProcessingError: If the message could not be processed
        """
        try:
            self.logger.info(f"Processing message for conversation: {conversation_id}")
            
            # Track start time for metrics
            start_time = datetime.now()
            
            # Create the message
            message = await self.create_message(
                content=content,
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                user_id=user_id,
                channel_id=channel_id,
                message_type=message_type,
                metadata=metadata
            )
            
            # Get the conversation
            try:
                conversation = await self.conversation_service.get_conversation(conversation_id)
            except Exception:
                # Create a new conversation if it doesn't exist
                self.logger.info(f"Conversation {conversation_id} not found, creating new conversation")
                conversation = await self.conversation_service.create_conversation(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    channel_id=channel_id,
                    metadata={"source": "message_processing"}
                )
            
            # Add the message to the conversation
            await self.conversation_service.add_message(conversation.id, message)
            
            # In a real implementation, we would generate a response here
            # For this example, we'll create a simple echo response
            response_content = f"Received: {content}"
            
            # Create a response message
            response_message = await self.create_message(
                content=response_content,
                conversation_id=conversation.id,
                tenant_id=tenant_id,
                user_id="system",  # System is the sender of response
                channel_id=channel_id,
                message_type="text",
                metadata={"is_response": True, "response_to": message.id}
            )
            
            # Add the response to the conversation
            conversation = await self.conversation_service.add_message(conversation.id, response_message)
            
            # Format the response
            response_data = self.format_response(
                message=message,
                response_message=response_message,
                conversation=conversation
            )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000  # in ms
            
            # Track metrics
            self.track_metrics(
                message=message,
                processing_time=processing_time,
                success=True
            )
            
            self.logger.info(f"Processed message for conversation: {conversation_id}")
            
            return response_data
            
        except Exception as e:
            self.logger.error(f"Failed to process message: {str(e)}", exc_info=True)
            
            # Track failed metrics
            if hasattr(self, 'metrics') and self.metrics:
                self.metrics.increment("message_processing_failures", {"error": type(e).__name__})
            
            raise ProcessingError(f"Failed to process message: {str(e)}")
    
    async def create_message(
        self,
        content: str,
        conversation_id: str,
        tenant_id: str,
        user_id: str,
        channel_id: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Create a new message.
        
        Args:
            content: Content of the message
            conversation_id: ID of the conversation
            tenant_id: ID of the tenant
            user_id: ID of the user
            channel_id: ID of the channel
            message_type: Type of the message
            metadata: Optional metadata for the message
            
        Returns:
            The created message
            
        Raises:
            RepositoryError: If the message could not be created
        """
        try:
            message_id = str(uuid.uuid4())
            
            message = Message(
                id=message_id,
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                sender_id=user_id,
                channel_id=channel_id,
                content=content,
                message_type=message_type,
                timestamp=datetime.now(),
                metadata=metadata or {}
            )
            
            self.logger.debug(f"Creating message: {message_id}")
            
            # Save the message
            saved_message = await self.repository.create(message)
            
            self.logger.debug(f"Created message: {message_id}")
            
            return saved_message
            
        except Exception as e:
            self.logger.error(f"Failed to create message: {str(e)}", exc_info=True)
            raise RepositoryError(f"Failed to create message: {str(e)}")
    
    def format_response(
        self,
        message: Message,
        response_message: Message,
        conversation: Conversation
    ) -> Dict[str, Any]:
        """
        Format a response message.
        
        Args:
            message: The original message
            response_message: The response message
            conversation: The conversation
            
        Returns:
            Formatted response data
        """
        return {
            "request": {
                "message_id": message.id,
                "content": message.content,
                "timestamp": message.timestamp.isoformat()
            },
            "response": {
                "message_id": response_message.id,
                "content": response_message.content,
                "timestamp": response_message.timestamp.isoformat()
            },
            "conversation": {
                "id": conversation.id,
                "message_count": len(conversation.messages),
                "started_at": conversation.started_at.isoformat(),
                "last_updated_at": conversation.last_updated_at.isoformat()
            }
        }
    
    async def save_message(self, message: Message) -> Message:
        """
        Save a message to the repository.
        
        Args:
            message: The message to save
            
        Returns:
            The saved message
            
        Raises:
            RepositoryError: If the message could not be saved
        """
        try:
            self.logger.debug(f"Saving message: {message.id}")
            
            saved_message = await self.repository.create(message)
            
            self.logger.debug(f"Saved message: {message.id}")
            
            return saved_message
            
        except Exception as e:
            self.logger.error(f"Failed to save message: {str(e)}", exc_info=True)
            raise RepositoryError(f"Failed to save message: {str(e)}")
    
    def track_metrics(
        self,
        message: Message,
        processing_time: float,
        success: bool
    ) -> None:
        """
        Track metrics for message processing.
        
        Args:
            message: The processed message
            processing_time: Time taken to process the message (ms)
            success: Whether processing was successful
        """
        if not hasattr(self, 'metrics') or not self.metrics:
            return
            
        try:
            # Record message processing
            self.metrics.increment(
                "messages_processed",
                {
                    "tenant_id": message.tenant_id,
                    "channel_id": message.channel_id,
                    "message_type": message.message_type,
                    "success": str(success)
                }
            )
            
            # Record processing time
            self.metrics.observe(
                "message_processing_time",
                processing_time,
                {
                    "tenant_id": message.tenant_id,
                    "channel_id": message.channel_id,
                    "message_type": message.message_type
                }
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to track metrics: {str(e)}")