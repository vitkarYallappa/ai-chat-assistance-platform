"""
Domain interfaces for the MCP service.

This package contains the abstract base classes that define the contracts
for various components in the MCP service domain layer. These interfaces
provide clean separation of concerns and enable dependency injection.
"""

from app.domain.interfaces.channel_interface import ChannelInterface
from app.domain.interfaces.normalizer_interface import NormalizerInterface

__all__ = [
    "ChannelInterface",
    "NormalizerInterface",
]