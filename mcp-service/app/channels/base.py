
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
import logging
from pydantic import BaseModel, ValidationError

from app.domain.models.message import Message
from app.domain.schemas.message import MessageResponse
from app.utils.exceptions import ChannelConfigError, MessageProcessingError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ChannelConfig(BaseModel):
    """Base configuration for channel implementations."""
    channel_id: str
    tenant_id: str
    enabled: bool = True
    
    class Config:
        extra = "allow"  # Allow additional fields for channel-specific config


class BaseChannel(ABC):
    """
    Abstract base class for all communication channel implementations.
    
    This class defines the standard interface that all channel implementations
    must conform to, ensuring consistent behavior across different messaging platforms.
    """
    
    def __init__(self, config: Union[Dict[str, Any], ChannelConfig]):
        """
        Initialize the channel with its configuration.
        
        Args:
            config: Configuration dictionary or ChannelConfig object
                   containing channel-specific settings
        
        Raises:
            ChannelConfigError: If configuration validation fails
        """
        try:
            self.config = config if isinstance(config, ChannelConfig) else ChannelConfig(**config)
            self.channel_id = self.config.channel_id
            self.tenant_id = self.config.tenant_id
            
            # Validate the configuration
            self.validate_config()
            
            logger.info(
                f"Initialized {self.__class__.__name__}",
                extra={
                    "channel_id": self.channel_id,
                    "tenant_id": self.tenant_id
                }
            )
        except ValidationError as e:
            logger.error(
                f"Failed to initialize {self.__class__.__name__}: Invalid configuration",
                extra={"errors": str(e)}
            )
            raise ChannelConfigError(f"Invalid channel configuration: {str(e)}")
        except Exception as e:
            logger.error(
                f"Failed to initialize {self.__class__.__name__}: {str(e)}",
                extra={"channel_id": getattr(self, "channel_id", None)}
            )
            raise ChannelConfigError(f"Channel initialization error: {str(e)}")
    
    @abstractmethod
    def send_message(self, message: Union[Message, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send message to the external channel.
        
        Args:
            message: Message to be sent, either as a Message object or dictionary
        
        Returns:
            Dictionary containing information about the sent message
            
        Raises:
            MessageProcessingError: If message sending fails
        """
        pass
    
    @abstractmethod
    def receive_message(self, payload: Dict[str, Any]) -> Message:
        """
        Process and normalize incoming message from the channel.
        
        Args:
            payload: Raw message payload from the channel
            
        Returns:
            Normalized Message object
            
        Raises:
            MessageProcessingError: If message processing fails
        """
        pass
    
    @abstractmethod
    def normalize_message(self, payload: Dict[str, Any]) -> Message:
        """
        Convert channel-specific message format to internal Message model.
        
        Args:
            payload: Raw message payload from the channel
            
        Returns:
            Normalized Message object
            
        Raises:
            MessageProcessingError: If normalization fails
        """
        pass
    
    @abstractmethod
    def format_response(self, message: Union[Message, MessageResponse]) -> Dict[str, Any]:
        """
        Format internal message for channel-specific delivery format.
        
        Args:
            message: Internal message to format
            
        Returns:
            Channel-specific formatted message payload
            
        Raises:
            MessageProcessingError: If formatting fails
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate channel configuration.
        
        This method should be overridden by subclasses to implement
        channel-specific configuration validation.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ChannelConfigError: If configuration is invalid
        """
        # Base validation checks
        if not self.config.enabled:
            logger.warning(
                f"Channel {self.channel_id} is disabled",
                extra={"tenant_id": self.tenant_id}
            )
        
        return True
    
    def __str__(self) -> str:
        """String representation of the channel instance."""
        return f"{self.__class__.__name__}(channel_id={self.channel_id}, tenant_id={self.tenant_id})"
    
    def is_enabled(self) -> bool:
        """Check if the channel is enabled."""
        return self.config.enabled