"""
WhatsApp Channel implementation for the MCP Service.

This package provides the necessary components to integrate with the WhatsApp Business API,
including the channel implementation, client, and utility functions.
"""

from app.channels.whatsapp.channel import WhatsAppChannel, WhatsAppChannelConfig
from app.channels.whatsapp.client import WhatsAppClient

__all__ = [
    'WhatsAppChannel',
    'WhatsAppChannelConfig',
    'WhatsAppClient'
]