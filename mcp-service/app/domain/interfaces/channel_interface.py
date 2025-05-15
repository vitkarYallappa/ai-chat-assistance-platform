"""
Channel interface that defines the contract for all messaging channel implementations.

This interface specifies the methods that all channel implementations must provide
to ensure consistent behavior across different messaging platforms.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.domain.models.message import Message


class ChannelInterface(ABC):
    """
    Abstract base class for all channel implementations.
    
    A channel represents a messaging platform (WhatsApp, Facebook Messenger, etc.)
    and encapsulates all platform-specific logic for sending and receiving messages.
    """
    
    @abstractmethod
    async def send_message(self, message: Message, tenant_id: str) -> Dict[str, Any]:
        """
        Sends a message to the channel.
        
        Args:
            message: The normalized message to send
            tenant_id: The tenant identifier
            
        Returns:
            Dict containing the delivery information including channel-specific message IDs
            
        Raises:
            ChannelException: If message delivery fails
        """
        pass
    
    @abstractmethod
    async def receive_message(self, payload: Dict[str, Any], tenant_id: str) -> Message:
        """
        Processes an incoming message from the channel.
        
        Args:
            payload: The raw webhook payload from the channel
            tenant_id: The tenant identifier
            
        Returns:
            A normalized Message object
            
        Raises:
            ValidationException: If the message payload is invalid
            ChannelException: If message processing fails
        """
        pass
    
    @abstractmethod
    async def normalize_message(self, raw_message: Dict[str, Any]) -> Message:
        """
        Converts a channel-specific message format to the internal normalized format.
        
        Args:
            raw_message: The raw message data from the channel
            
        Returns:
            A normalized Message object
            
        Raises:
            ValidationException: If the message cannot be normalized
        """
        pass
    
    @abstractmethod
    async def format_response(self, message: Message) -> Dict[str, Any]:
        """
        Converts an internal normalized message to the channel-specific format.
        
        Args:
            message: The normalized message to format
            
        Returns:
            A dictionary containing the channel-specific message format
            
        Raises:
            ValidationException: If the message cannot be formatted
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Returns the capabilities of this channel.
        
        Capabilities define what message types and features are supported by this channel.
        
        Returns:
            A dictionary of channel capabilities (supported message types, features, etc.)
        """
        pass
    
    @abstractmethod
    async def verify_webhook_signature(self, 
                                       payload: bytes, 
                                       signature: str, 
                                       tenant_id: str) -> bool:
        """
        Verifies the signature of an incoming webhook.
        
        Args:
            payload: The raw webhook payload
            signature: The signature provided in the webhook headers
            tenant_id: The tenant identifier
            
        Returns:
            True if the signature is valid, False otherwise
        """
        pass

    @abstractmethod
    async def is_enabled(self, tenant_id: str) -> bool:
        """
        Checks if this channel is enabled for the specified tenant.
        
        Args:
            tenant_id: The tenant identifier
            
        Returns:
            True if the channel is enabled, False otherwise
        """
        pass