"""
Main application package for the MCP service.

This is the root package for the MCP service application, containing the 
main application factory and configuration components.
"""

from app.config import Settings, get_settings, load_env_file
from app.main import (
    create_application,
    register_routers,
    configure_middleware,
    configure_websocket
)

__all__ = [
    # Configuration
    "Settings",
    "get_settings",
    "load_env_file",
    
    # Application factory
    "create_application",
    "register_routers",
    "configure_middleware",
    "configure_websocket",
]