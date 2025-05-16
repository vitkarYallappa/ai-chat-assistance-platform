from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.utils.logger import get_logger
from app.domain.models.message import Message


class BaseFormatter(ABC):
    """
    Abstract base formatter that defines the interface for all formatter implementations.
    Follows the Strategy pattern to allow switching between different formatting strategies.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the formatter with optional configuration.
        
        Args:
            config: Optional configuration dictionary for the formatter
        """
        self.logger = get_logger(__name__)
        self.config = config or {}
    
    @abstractmethod
    def format(self, message: Message, channel_id: str) -> Dict[str, Any]:
        """
        Format a message for a specific channel.
        
        Args:
            message: The message to format
            channel_id: The ID of the channel to format for
            
        Returns:
            A dictionary containing the formatted message
        """
        pass
    
    def supports(self, message_type: str) -> bool:
        """
        Check if this formatter supports a specific message type.
        
        Args:
            message_type: The type of message to check
            
        Returns:
            True if this formatter supports the message type, False otherwise
        """
        supported_types = self.get_supported_types()
        return message_type in supported_types
    
    def get_supported_types(self) -> list[str]:
        """
        Get the message types supported by this formatter.
        
        Returns:
            A list of supported message types
        """
        return []
    
    def process_metadata(self, message: Message) -> Dict[str, Any]:
        """
        Process message metadata for formatting.
        
        Args:
            message: The message containing metadata
            
        Returns:
            A dictionary of processed metadata
        """
        metadata = message.metadata or {}
        
        # Extract common metadata fields
        result = {
            "message_id": message.id,
            "timestamp": message.timestamp.isoformat(),
            "sender_id": message.sender_id,
        }
        
        # Add custom metadata if present
        if metadata:
            result["custom_metadata"] = metadata
            
        return result
    
    def validate_formatting_limits(self, message: Message, channel_id: str) -> bool:
        """
        Validate if the message meets the formatting limits for the channel.
        
        Args:
            message: The message to validate
            channel_id: The ID of the channel
            
        Returns:
            True if the message meets the limits, False otherwise
        """
        self.logger.debug(f"Validating formatting limits for channel {channel_id}")
        # Default implementation - override in concrete classes
        return True