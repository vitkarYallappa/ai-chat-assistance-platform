"""
Text Message Normalizer Module.

This module implements the normalizer for text messages in the MCP Service.
The TextNormalizer converts channel-specific text message formats to/from
the standardized internal format.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.domain.models.message import Message, MessageType
from app.normalizers.base import BaseNormalizer
from app.utils.logger import get_logger
from app.utils.exceptions import NormalizationError, ValidationError

logger = get_logger(__name__)

# Common entity patterns for extraction
ENTITY_PATTERNS = {
    "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "phone": r'\b\+?[0-9]{1,3}[-.\s]?[0-9]{3}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}\b',
    "url": r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*\??[/\w\.-=%&]*',
    "hashtag": r'#[A-Za-z0-9_]+',
    "mention": r'@[A-Za-z0-9_]+',
    "date": r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
    "time": r'\b(?:\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)\b',
    "currency": r'\b(?:[$€£¥]|USD|EUR|GBP|JPY)\s?\d+(?:\.\d{2})?\b',
}


class TextNormalizer(BaseNormalizer):
    """
    Normalizer for text messages across different channels.
    
    Converts channel-specific text message formats to/from the standardized
    internal message format.
    """
    
    def __init__(self, channel_id: str, tenant_id: str, 
                 max_length: int = 4096, 
                 detect_entities: bool = True,
                 sanitize_input: bool = True):
        """
        Initialize the text normalizer with configuration.
        
        Args:
            channel_id (str): The identifier for the messaging channel
            tenant_id (str): The identifier for the tenant
            max_length (int): Maximum allowed message length
            detect_entities (bool): Whether to detect entities in text
            sanitize_input (bool): Whether to sanitize input text
        """
        super().__init__(channel_id, tenant_id)
        self.max_length = max_length
        self.detect_entities = detect_entities
        self.sanitize_input = sanitize_input
        
        # Compile regex patterns for performance
        self.entity_patterns = {
            entity_type: re.compile(pattern) 
            for entity_type, pattern in ENTITY_PATTERNS.items()
        }
    
    def normalize(self, channel_message: Dict[str, Any]) -> Message:
        """
        Convert a channel-specific text message to the standardized internal format.
        
        Args:
            channel_message (Dict[str, Any]): Text message in channel-specific format
            
        Returns:
            Message: Text message in standardized internal format
            
        Raises:
            NormalizationError: If the message cannot be normalized
            ValidationError: If the message validation fails
        """
        self._log_normalization_attempt('normalize')
        
        try:
            # Validate the input message
            self.validate(channel_message)
            
            # Extract basic message properties
            sender_id = self._extract_sender_id(channel_message)
            text_content = self._extract_text_content(channel_message)
            message_id = self._extract_message_id(channel_message)
            timestamp = self._extract_timestamp(channel_message)
            
            # Clean the text if sanitization is enabled
            if self.sanitize_input:
                text_content = self.clean_text(text_content)
            
            # Extract entities if enabled
            entities = {}
            if self.detect_entities:
                entities = self.extract_entities(text_content)
            
            # Extract any additional metadata
            metadata = self.extract_metadata(channel_message)
            
            # Create and return the normalized message
            return Message(
                message_id=message_id,
                channel_id=self.channel_id,
                tenant_id=self.tenant_id,
                sender_id=sender_id,
                message_type=MessageType.TEXT,
                content=text_content,
                entities=entities,
                metadata=metadata,
                timestamp=timestamp
            )
        
        except (KeyError, ValueError) as e:
            error_msg = f"Failed to normalize text message: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise NormalizationError(error_msg) from e
    
    def denormalize(self, message: Message) -> Dict[str, Any]:
        """
        Convert a standardized internal message to the channel-specific text format.
        
        Args:
            message (Message): Message in standardized internal format
            
        Returns:
            Dict[str, Any]: Text message in channel-specific format
            
        Raises:
            NormalizationError: If the message cannot be denormalized
            ValidationError: If the message validation fails
        """
        self._log_normalization_attempt('denormalize', message.message_id)
        
        try:
            # Validate the message is a text message
            if message.message_type != MessageType.TEXT:
                raise ValidationError(
                    f"Cannot denormalize non-text message with type {message.message_type}"
                )
            
            # Basic channel-specific message structure
            # This is a generic implementation that should be overridden by channel-specific normalizers
            channel_message = {
                "id": message.message_id,
                "text": message.content,
                "sender": message.sender_id,
                "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                "channel": self.channel_id,
                "tenant": self.tenant_id
            }
            
            # Add any additional metadata
            if message.metadata:
                channel_message["metadata"] = message.metadata
            
            return channel_message
        
        except Exception as e:
            error_msg = f"Failed to denormalize text message {message.message_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise NormalizationError(error_msg) from e
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities like emails, URLs, phone numbers, etc. from text.
        
        Args:
            text (str): The text to extract entities from
            
        Returns:
            Dict[str, List[str]]: Dictionary with entity types as keys and lists of
                                detected entities as values
        """
        if not text:
            return {}
        
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = pattern.findall(text)
            if matches:
                entities[entity_type] = list(set(matches))  # Deduplicate matches
        
        return entities
    
    def clean_text(self, text: str) -> str:
        """
        Sanitize and format text to prevent security issues and ensure consistency.
        
        Args:
            text (str): The text to clean
            
        Returns:
            str: The cleaned text
        """
        if not text:
            return ""
        
        # Remove any control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Trim whitespace and normalize spaces
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Truncate if exceeding max length
        if len(text) > self.max_length:
            text = text[:self.max_length - 3] + "..."
            logger.warning(f"Text message truncated to {self.max_length} characters")
        
        return text
    
    def validate(self, channel_message: Dict[str, Any]) -> bool:
        """
        Validate the structure of a channel-specific text message.
        
        Args:
            channel_message (Dict[str, Any]): The message to validate
            
        Returns:
            bool: True if the message is valid, False otherwise
            
        Raises:
            ValidationError: If the message validation fails with specific details
        """
        super().validate(channel_message)
        
        # Ensure the message is a dictionary
        if not isinstance(channel_message, dict):
            raise ValidationError(f"Expected dict, got {type(channel_message).__name__}")
        
        # Check for required fields (this will be channel-specific in concrete implementations)
        required_fields = self._get_required_fields()
        missing_fields = [field for field in required_fields if field not in channel_message]
        
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # If we've made it this far, the message is valid
        return True
    
    def _extract_sender_id(self, channel_message: Dict[str, Any]) -> str:
        """
        Extract the sender ID from a channel-specific message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            str: The sender ID
            
        Raises:
            KeyError: If the sender ID cannot be extracted
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        # Different channels might store sender ID in different fields
        for field in ['sender_id', 'sender', 'from', 'user_id', 'from_user']:
            if field in channel_message:
                return str(channel_message[field])
        
        raise KeyError("Could not find sender ID in channel message")
    
    def _extract_text_content(self, channel_message: Dict[str, Any]) -> str:
        """
        Extract the text content from a channel-specific message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            str: The text content
            
        Raises:
            KeyError: If the text content cannot be extracted
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        for field in ['text', 'content', 'message', 'body']:
            if field in channel_message:
                return str(channel_message[field])
        
        raise KeyError("Could not find text content in channel message")
    
    def _extract_message_id(self, channel_message: Dict[str, Any]) -> str:
        """
        Extract the message ID from a channel-specific message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            str: The message ID
            
        Raises:
            KeyError: If the message ID cannot be extracted
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        for field in ['id', 'message_id', 'msg_id']:
            if field in channel_message:
                return str(channel_message[field])
        
        raise KeyError("Could not find message ID in channel message")
    
    def _extract_timestamp(self, channel_message: Dict[str, Any]) -> Optional[str]:
        """
        Extract the timestamp from a channel-specific message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            Optional[str]: The timestamp, or None if not found
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        for field in ['timestamp', 'time', 'date', 'created_at']:
            if field in channel_message:
                return channel_message[field]
        
        return None
    
    def _get_required_fields(self) -> Set[str]:
        """
        Get the set of required fields for a valid channel-specific message.
        
        Returns:
            Set[str]: Set of required field names
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        # At minimum, we need some way to identify the message and its content
        return {'id', 'text'}
    
    def _get_message_type(self, channel_message: Dict[str, Any]) -> str:
        """
        Determine if a channel-specific message is a text message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            str: Message type, "text" if it's a text message
        """
        # Check for common fields that indicate a text message
        # This is a generic implementation that should be overridden by channel-specific normalizers
        if any(field in channel_message for field in ['text', 'content', 'message', 'body']):
            return "text"
        
        return "unknown"