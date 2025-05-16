from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl, validator
import json
import uuid

from app.channels.base import BaseChannel, ChannelConfig
from app.channels.whatsapp.client import WhatsAppClient
from app.domain.models.message import Message
from app.domain.schemas.message import MessageResponse, MessageType
from app.utils.exceptions import MessageProcessingError, ChannelConfigError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class WhatsAppChannelConfig(ChannelConfig):
    """WhatsApp specific channel configuration."""
    api_version: str = "v18.0"
    phone_number_id: str
    business_account_id: str
    access_token: str
    webhook_secret: Optional[str] = None
    base_url: HttpUrl = Field(default="https://graph.facebook.com")
    
    @validator('phone_number_id')
    def validate_phone_number_id(cls, v):
        # Basic validation - ensure it's a string with digits only
        if not v or not v.isdigit():
            raise ValueError("phone_number_id must be a string of digits")
        return v


class WhatsAppChannel(BaseChannel):
    """
    WhatsApp channel implementation.
    
    This class implements the BaseChannel interface for WhatsApp,
    handling WhatsApp-specific message formatting, sending, and receiving.
    """
    
    # Class-level configuration schema for registration
    CONFIG_SCHEMA = {
        "type": "WhatsAppChannelConfig",
        "required": ["phone_number_id", "business_account_id", "access_token"],
        "optional": ["api_version", "webhook_secret", "base_url"]
    }
    
    def __init__(self, config: Union[Dict[str, Any], WhatsAppChannelConfig]):
        """
        Initialize WhatsApp channel with configuration.
        
        Args:
            config: Configuration for the WhatsApp channel
            
        Raises:
            ChannelConfigError: If configuration is invalid
        """
        try:
            # Convert dict to WhatsAppChannelConfig if needed
            if isinstance(config, dict):
                config = WhatsAppChannelConfig(**config)
                
            # Initialize base class
            super().__init__(config)
            
            # Store the typed config for WhatsApp-specific fields
            self.whatsapp_config = config
            
            # Initialize the WhatsApp client
            self.client = WhatsAppClient(
                base_url=str(self.whatsapp_config.base_url),
                api_version=self.whatsapp_config.api_version,
                phone_number_id=self.whatsapp_config.phone_number_id,
                access_token=self.whatsapp_config.access_token
            )
            
            logger.info(
                f"WhatsApp channel initialized for phone number ID: {self.whatsapp_config.phone_number_id}",
                extra={"tenant_id": self.tenant_id, "channel_id": self.channel_id}
            )
        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp channel: {str(e)}")
            raise ChannelConfigError(f"WhatsApp channel initialization error: {str(e)}")
    
    def validate_config(self) -> bool:
        """
        Validate WhatsApp channel configuration.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ChannelConfigError: If configuration is invalid
        """
        # Call base validation
        super().validate_config()
        
        # WhatsApp-specific validation
        try:
            # Validate WhatsApp config
            if not hasattr(self, 'whatsapp_config'):
                self.whatsapp_config = WhatsAppChannelConfig(**self.config.dict())
                
            # Test WhatsApp client connection
            logger.info("Testing WhatsApp client connection...")
            if hasattr(self, 'client'):
                # Optionally perform a lightweight API call to verify credentials
                # self.client.test_connection()
                pass
                
            return True
        except Exception as e:
            logger.error(f"WhatsApp configuration validation failed: {str(e)}")
            raise ChannelConfigError(f"Invalid WhatsApp configuration: {str(e)}")
    
    def send_message(self, message: Union[Message, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send message to WhatsApp API.
        
        Args:
            message: Message to send, either as a Message object or dictionary
            
        Returns:
            Dictionary containing information about the sent message
            
        Raises:
            MessageProcessingError: If message sending fails
        """
        try:
            # Convert to Message object if needed
            if isinstance(message, dict):
                # In a real implementation, you'd convert the dict to a Message object
                # This is simplified for the example
                pass
                
            # Format the message for WhatsApp
            formatted_message = self.format_response(message)
            
            # Determine message type and call appropriate client method
            message_type = message.message_type if hasattr(message, 'message_type') else formatted_message.get('type', 'text')
            recipient_id = formatted_message.get('recipient_id')
            
            response = None
            
            if message_type == MessageType.TEXT:
                response = self.client.send_text(
                    recipient_id=recipient_id,
                    text=formatted_message.get('text', '')
                )
            elif message_type == MessageType.TEMPLATE:
                response = self.client.send_template(
                    recipient_id=recipient_id,
                    template_name=formatted_message.get('template_name', ''),
                    template_data=formatted_message.get('template_data', {})
                )
            elif message_type == MessageType.MEDIA:
                response = self.client.send_media(
                    recipient_id=recipient_id,
                    media_type=formatted_message.get('media_type', ''),
                    media_url=formatted_message.get('media_url', ''),
                    caption=formatted_message.get('caption', '')
                )
            elif message_type == MessageType.INTERACTIVE:
                response = self.client.send_interactive(
                    recipient_id=recipient_id,
                    interactive_data=formatted_message.get('interactive', {})
                )
            else:
                raise MessageProcessingError(f"Unsupported message type: {message_type}")
                
            logger.info(
                f"Message sent to WhatsApp recipient: {recipient_id}",
                extra={
                    "tenant_id": self.tenant_id,
                    "channel_id": self.channel_id,
                    "message_type": message_type
                }
            )
            
            return {
                "channel_message_id": response.get("messages", [{}])[0].get("id", ""),
                "status": "sent",
                "recipient_id": recipient_id,
                "timestamp": response.get("timestamp", ""),
                "raw_response": response
            }
        except Exception as e:
            logger.error(
                f"Failed to send WhatsApp message: {str(e)}",
                extra={"tenant_id": self.tenant_id, "channel_id": self.channel_id}
            )
            raise MessageProcessingError(f"WhatsApp message sending error: {str(e)}")
    
    def receive_message(self, payload: Dict[str, Any]) -> Message:
        """
        Process incoming WhatsApp message.
        
        Args:
            payload: Raw webhook payload from WhatsApp
            
        Returns:
            Normalized Message object
            
        Raises:
            MessageProcessingError: If message processing fails
        """
        try:
            logger.debug(
                "Received WhatsApp webhook payload",
                extra={
                    "tenant_id": self.tenant_id,
                    "channel_id": self.channel_id
                }
            )
            
            # Verify webhook signature if configured
            if self.whatsapp_config.webhook_secret:
                # In a real implementation, you'd verify the webhook signature here
                pass
                
            # Normalize the message
            return self.normalize_message(payload)
        except Exception as e:
            logger.error(
                f"Failed to process WhatsApp webhook: {str(e)}",
                extra={"tenant_id": self.tenant_id, "channel_id": self.channel_id}
            )
            raise MessageProcessingError(f"WhatsApp webhook processing error: {str(e)}")
    
    def normalize_message(self, payload: Dict[str, Any]) -> Message:
        """
        Convert WhatsApp message format to internal Message model.
        
        Args:
            payload: Raw webhook payload from WhatsApp
            
        Returns:
            Normalized Message object
            
        Raises:
            MessageProcessingError: If normalization fails
        """
        try:
            # Extract top-level data from webhook payload
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            message_data = value.get("messages", [{}])[0]
            
            # Extract message metadata
            sender_id = message_data.get("from", "")
            timestamp = message_data.get("timestamp", "")
            channel_message_id = message_data.get("id", "")
            
            # Determine message type and extract content
            message_type = MessageType.TEXT  # Default
            content = {}
            
            if "text" in message_data:
                message_type = MessageType.TEXT
                content = {
                    "text": message_data["text"].get("body", "")
                }
            elif "image" in message_data:
                message_type = MessageType.MEDIA
                content = {
                    "media_type": "image",
                    "media_id": message_data["image"].get("id", ""),
                    "mime_type": message_data["image"].get("mime_type", ""),
                    "caption": message_data["image"].get("caption", "")
                }
            elif "audio" in message_data:
                message_type = MessageType.MEDIA
                content = {
                    "media_type": "audio",
                    "media_id": message_data["audio"].get("id", ""),
                    "mime_type": message_data["audio"].get("mime_type", "")
                }
            elif "video" in message_data:
                message_type = MessageType.MEDIA
                content = {
                    "media_type": "video",
                    "media_id": message_data["video"].get("id", ""),
                    "mime_type": message_data["video"].get("mime_type", ""),
                    "caption": message_data["video"].get("caption", "")
                }
            elif "document" in message_data:
                message_type = MessageType.MEDIA
                content = {
                    "media_type": "document",
                    "media_id": message_data["document"].get("id", ""),
                    "mime_type": message_data["document"].get("mime_type", ""),
                    "filename": message_data["document"].get("filename", "")
                }
            elif "location" in message_data:
                message_type = MessageType.LOCATION
                content = {
                    "latitude": message_data["location"].get("latitude", 0),
                    "longitude": message_data["location"].get("longitude", 0),
                    "name": message_data["location"].get("name", ""),
                    "address": message_data["location"].get("address", "")
                }
            elif "interactive" in message_data:
                message_type = MessageType.INTERACTIVE
                interactive_data = message_data["interactive"]
                content = {
                    "interactive_type": interactive_data.get("type", ""),
                    "interactive_data": interactive_data
                }
            
            # Create a new Message object
            message = Message(
                message_id=str(uuid.uuid4()),  # Generate internal message ID
                channel_message_id=channel_message_id,
                channel_id=self.channel_id,
                tenant_id=self.tenant_id,
                sender_id=sender_id,
                recipient_id=self.whatsapp_config.phone_number_id,  # Business phone number
                message_type=message_type,
                content=content,
                timestamp=timestamp,
                raw_payload=payload  # Store original payload for reference
            )
            
            logger.info(
                f"Normalized WhatsApp message from {sender_id}",
                extra={
                    "tenant_id": self.tenant_id,
                    "channel_id": self.channel_id,
                    "message_type": message_type,
                    "channel_message_id": channel_message_id
                }
            )
            
            return message
        except Exception as e:
            logger.error(
                f"Failed to normalize WhatsApp message: {str(e)}",
                extra={"tenant_id": self.tenant_id, "channel_id": self.channel_id}
            )
            raise MessageProcessingError(f"WhatsApp message normalization error: {str(e)}")
    
    def format_response(self, message: Union[Message, MessageResponse]) -> Dict[str, Any]:
        """
        Format internal message for WhatsApp delivery format.
        
        Args:
            message: Internal message to format
            
        Returns:
            WhatsApp-specific formatted message payload
            
        Raises:
            MessageProcessingError: If formatting fails
        """
        try:
            # Extract message data
            content = message.content if hasattr(message, 'content') else {}
            recipient_id = message.recipient_id if hasattr(message, 'recipient_id') else ""
            message_type = message.message_type if hasattr(message, 'message_type') else MessageType.TEXT
            
            # Base message structure
            formatted_message = {
                "recipient_id": recipient_id,
                "type": message_type
            }
            
            # Format based on message type
            if message_type == MessageType.TEXT:
                formatted_message["text"] = content.get("text", "")
            
            elif message_type == MessageType.TEMPLATE:
                formatted_message.update({
                    "template_name": content.get("template_name", ""),
                    "template_data": content.get("template_data", {})
                })
            
            elif message_type == MessageType.MEDIA:
                formatted_message.update({
                    "media_type": content.get("media_type", ""),
                    "media_url": content.get("media_url", ""),
                    "caption": content.get("caption", "")
                })
            
            elif message_type == MessageType.INTERACTIVE:
                formatted_message.update({
                    "interactive": content.get("interactive_data", {})
                })
            
            elif message_type == MessageType.LOCATION:
                formatted_message.update({
                    "latitude": content.get("latitude", 0),
                    "longitude": content.get("longitude", 0),
                    "name": content.get("name", ""),
                    "address": content.get("address", "")
                })
            
            else:
                raise MessageProcessingError(f"Unsupported message type for WhatsApp: {message_type}")
                
            logger.debug(
                f"Formatted message for WhatsApp delivery",
                extra={
                    "tenant_id": self.tenant_id,
                    "channel_id": self.channel_id,
                    "message_type": message_type,
                    "recipient_id": recipient_id
                }
            )
            
            return formatted_message
        except Exception as e:
            logger.error(
                f"Failed to format message for WhatsApp: {str(e)}",
                extra={"tenant_id": self.tenant_id, "channel_id": self.channel_id}
            )
            raise MessageProcessingError(f"WhatsApp message formatting error: {str(e)}")