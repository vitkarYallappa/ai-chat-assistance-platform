"""
Normalizer interface for standardizing message formats across different channels.

This interface defines the methods that message normalizers must implement to convert
between channel-specific formats and the internal normalized format.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List

from app.domain.models.message import Message


class NormalizerInterface(ABC):
    """
    Abstract base class for message normalizers.
    
    Normalizers convert channel-specific message formats to a standardized internal format
    and vice versa, enabling consistent message handling across different channels.
    """
    
    @abstractmethod
    async def normalize(self, raw_message: Dict[str, Any], channel_id: str) -> Message:
        """
        Converts channel-specific message format to the internal normalized format.
        
        Args:
            raw_message: The raw message data from the channel
            channel_id: The identifier of the source channel
            
        Returns:
            A normalized Message object
            
        Raises:
            ValidationException: If the message cannot be normalized
        """
        pass
    
    @abstractmethod
    async def denormalize(self, message: Message, channel_id: str) -> Dict[str, Any]:
        """
        Converts a normalized message to channel-specific format.
        
        Args:
            message: The normalized message to convert
            channel_id: The identifier of the target channel
            
        Returns:
            A dictionary containing the channel-specific message format
            
        Raises:
            ValidationException: If the message cannot be denormalized
        """
        pass
    
    @abstractmethod
    def supports_type(self, message_type: str, content_type: str) -> bool:
        """
        Checks if this normalizer supports the given message and content type.
        
        Args:
            message_type: The type of message (text, image, etc.)
            content_type: The type of content (text/plain, image/jpeg, etc.)
            
        Returns:
            True if this normalizer supports the message and content type, False otherwise
        """
        pass
    
    @abstractmethod
    async def extract_metadata(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts metadata from a raw message.
        
        Metadata includes information like sender details, timestamps, etc. that are not
        part of the message content but are important for message processing.
        
        Args:
            raw_message: The raw message data
            
        Returns:
            A dictionary containing message metadata
        """
        pass
    
    @abstractmethod
    async def validate(self, message: Message) -> bool:
        """
        Validates a normalized message.
        
        Args:
            message: The message to validate
            
        Returns:
            True if the message is valid, False otherwise
            
        Raises:
            ValidationException: If the message is invalid with detailed validation errors
        """
        pass