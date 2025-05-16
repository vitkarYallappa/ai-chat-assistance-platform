"""
Channel implementations for the MCP Service.

This package contains the base channel interface and factory as well as
concrete implementations for various messaging platforms.
"""

from app.channels.base import BaseChannel, ChannelConfig
from app.channels.channel_factory import ChannelFactory

# Import channel implementations for auto-registration
from app.channels.whatsapp import WhatsAppChannel

# Register built-in channel types with the factory
ChannelFactory.register_channel("whatsapp", WhatsAppChannel)

# Initialize the factory to discover additional channel implementations
ChannelFactory.initialize()

__all__ = [
    'BaseChannel',
    'ChannelConfig',
    'ChannelFactory',
    'WhatsAppChannel'
]