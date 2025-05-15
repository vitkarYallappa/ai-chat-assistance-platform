"""
WebSocket implementation package for the MCP service.

This package contains WebSocket-related components for real-time communication,
including the connection manager and message handlers.
"""

from app.api.websocket.connection_manager import (
    ConnectionManager,
    connect,
    disconnect,
    send_message,
    broadcast
)

# Create a singleton connection manager instance
connection_manager = ConnectionManager()

__all__ = [
    # Classes
    "ConnectionManager",
    
    # Functions
    "connect",
    "disconnect",
    "send_message",
    "broadcast",
    
    # Instances
    "connection_manager",
]