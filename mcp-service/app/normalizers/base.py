"""
Base Normalizer Module.

This module defines the abstract base class for all message normalizers in the MCP Service.
Normalizers are responsible for converting channel-specific message formats to/from
a standardized internal format used throughout the system.
"""

import abc
from typing import Any, Dict, Optional, TypeVar, Generic, List

from app.domain.models.message import Message
from app.utils.logger import get_logger
from app.utils.exceptions import NormalizationError, ValidationError

T = TypeVar('T')  # Generic type for channel-specific message formats

logger = get_logger(__name__)


class BaseNormalizer(Generic[T], abc.ABC):
    """
    Abstract base class for all message normalizers.
    
    Each messaging channel (WhatsApp, Facebook, Telegram, etc.) requires a specific
    normalizer implementation to convert between channel-specific and internal formats.
    """
    
    def __init__(self, channel_id: str, tenant_id: str):
        """
        Initialize the normalizer with channel and tenant identifiers.
        
        Args:
            channel_id (str): The identifier for the messaging channel
            tenant_id (str): The identifier for the tenant
        """
        self.channel_id = channel_id
        self.tenant_id = tenant_id
        logger.debug(f"Initialized {self.__class__.__name__} for channel={channel_id}, tenant={tenant_id}")
    
    @abc.abstractmethod
    def normalize(self, channel_message: T) -> Message:
        """
        Convert a channel-specific message to the standardized internal format.
        
        Args:
            channel_message (T): Message in channel-specific format
            
        Returns:
            Message: Message in standardized internal format
            
        Raises:
            NormalizationError: If the message cannot be normalized
        """
        pass
    
    @abc.abstractmethod
    def denormalize(self, message: Message) -> T:
        """
        Convert a standardized internal message to the channel-specific format.
        
        Args:
            message (Message): Message in standardized internal format
            
        Returns:
            T: Message in channel-specific format
            
        Raises:
            NormalizationError: If the message cannot be denormalized
        """
        pass
    
    def validate(self, message: Any) -> bool:
        """
        Validate the structure of a message.
        
        Args:
            message (Any): The message to validate (could be channel-specific or internal)
            
        Returns:
            bool: True if the message is valid, False otherwise
            
        Raises:
            ValidationError: If the message validation fails with specific details
        """
        # Base implementation just ensures message is not None
        if message is None:
            raise ValidationError("Message cannot be None")
        return True
    
    def extract_metadata(self, message: Any) -> Dict[str, Any]:
        """
        Extract metadata from a message.
        
        Args:
            message (Any): The message to extract metadata from
            
        Returns:
            Dict[str, Any]: Dictionary containing metadata key-value pairs
        """
        # Base implementation returns empty metadata
        # Child classes should override this to extract channel-specific metadata
        return {}
    
    def _get_message_type(self, channel_message: Any) -> str:
        """
        Determine the type of a message (text, image, audio, etc.).
        
        Args:
            channel_message (Any): The message to analyze
            
        Returns:
            str: The determined message type
        """
        # Default implementation assumes text
        # Child classes should override this to properly detect message types
        return "text"
    
    def _log_normalization_attempt(self, direction: str, message_id: Optional[str] = None) -> None:
        """
        Log details about a normalization attempt.
        
        Args:
            direction (str): Either 'normalize' or 'denormalize'
            message_id (Optional[str]): Message ID if available
        """
        msg_info = f" for message {message_id}" if message_id else ""
        logger.debug(
            f"Attempting to {direction} message{msg_info} using {self.__class__.__name__} "
            f"(channel={self.channel_id}, tenant={self.tenant_id})"
        )