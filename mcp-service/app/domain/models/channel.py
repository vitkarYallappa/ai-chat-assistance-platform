"""
Channel model representing a messaging platform integration.

This module defines the Channel class that represents a messaging platform
(WhatsApp, Facebook Messenger, etc.) and its configuration.
"""

from typing import Any, Dict, List, Optional, Set
from pydantic import validator


class Channel:
    """
    Represents a messaging channel in the system.
    
    A Channel encapsulates a messaging platform like WhatsApp, Facebook Messenger,
    Telegram, or Web Chat, along with its configuration for a specific tenant.
    """
    
    def __init__(
        self,
        channel_id: str,
        name: str,
        provider: str,
        config: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
        enabled: bool = True,
        supported_message_types: Optional[List[str]] = None,
        supported_content_types: Optional[Dict[str, List[str]]] = None,
        features: Optional[Dict[str, bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a new Channel instance.
        
        Args:
            channel_id: Unique identifier for the channel
            name: Display name of the channel
            provider: Provider of the channel (whatsapp, facebook, telegram, webchat)
            config: Channel-specific configuration
            tenant_id: Identifier of the tenant this channel belongs to
            enabled: Whether this channel is enabled
            supported_message_types: List of message types supported by this channel
            supported_content_types: Dictionary mapping message types to supported content types
            features: Dictionary of feature flags for this channel
            metadata: Additional metadata for this channel
        """
        self.channel_id = channel_id
        self.name = name
        self.provider = provider
        self.config = config or {}
        self.tenant_id = tenant_id
        self.enabled = enabled
        self.supported_message_types = supported_message_types or []
        self.supported_content_types = supported_content_types or {}
        self.features = features or {}
        self.metadata = metadata or {}
    
    def is_enabled(self, tenant_id: Optional[str] = None) -> bool:
        """
        Check if this channel is enabled for the specified tenant.
        
        Args:
            tenant_id: The tenant to check (defaults to the channel's tenant)
            
        Returns:
            True if the channel is enabled, False otherwise
        """
        # If tenant_id is provided, check if it matches the channel's tenant
        if tenant_id and self.tenant_id and tenant_id != self.tenant_id:
            return False
        
        return self.enabled
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this channel.
        
        Returns:
            Dictionary containing the channel's capabilities
        """
        return {
            "supported_message_types": self.supported_message_types,
            "supported_content_types": self.supported_content_types,
            "features": self.features,
        }
    
    def supports_message_type(self, message_type: str) -> bool:
        """
        Check if this channel supports the specified message type.
        
        Args:
            message_type: The message type to check
            
        Returns:
            True if the message type is supported, False otherwise
        """
        return message_type in self.supported_message_types
    
    def supports_content_type(self, message_type: str, content_type: str) -> bool:
        """
        Check if this channel supports the specified content type for a message type.
        
        Args:
            message_type: The message type
            content_type: The content type to check
            
        Returns:
            True if the content type is supported for the message type, False otherwise
        """
        if not self.supports_message_type(message_type):
            return False
        
        supported_types = self.supported_content_types.get(message_type, [])
        return content_type in supported_types
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the channel to a dictionary representation.
        
        Returns:
            Dictionary representation of the channel
        """
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "provider": self.provider,
            "config": self.config,
            "tenant_id": self.tenant_id,
            "enabled": self.enabled,
            "supported_message_types": self.supported_message_types,
            "supported_content_types": self.supported_content_types,
            "features": self.features,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Channel":
        """
        Create a channel from a dictionary representation.
        
        Args:
            data: Dictionary representation of a channel
            
        Returns:
            A new Channel instance
        """
        return cls(**data)
    
    def __repr__(self) -> str:
        """String representation of the channel for debugging."""
        return (f"Channel(channel_id={self.channel_id}, "
                f"name={self.name}, "
                f"provider={self.provider}, "
                f"tenant_id={self.tenant_id}, "
                f"enabled={self.enabled})")