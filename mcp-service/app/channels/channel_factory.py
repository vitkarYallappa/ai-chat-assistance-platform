from typing import Any, Dict, List, Optional, Type
import importlib
import inspect

from app.utils.logger import get_logger
from app.utils.exceptions import ChannelNotFoundError, ChannelRegistrationError
from app.channels.base import BaseChannel

logger = get_logger(__name__)

class ChannelFactory:
    """
    Factory for creating and managing channel instances.
    
    This class implements the Factory pattern to create instances of channel
    implementations based on configuration. It maintains a registry of available
    channel types and their corresponding implementation classes.
    """
    
    # Class-level registry of channel types to implementation classes
    _registry: Dict[str, Type[BaseChannel]] = {}
    
    @classmethod
    def register_channel(cls, channel_type: str, channel_class: Type[BaseChannel]) -> None:
        """
        Register a new channel implementation.
        
        Args:
            channel_type: Unique identifier for the channel type
            channel_class: The channel implementation class (must extend BaseChannel)
            
        Raises:
            ChannelRegistrationError: If registration fails or channel_class is invalid
        """
        if not channel_type:
            raise ChannelRegistrationError("Channel type cannot be empty")
            
        if not inspect.isclass(channel_class) or not issubclass(channel_class, BaseChannel):
            raise ChannelRegistrationError(
                f"Channel class must be a subclass of BaseChannel, got {channel_class}"
            )
            
        if channel_type in cls._registry:
            logger.warning(f"Overriding existing channel type: {channel_type}")
            
        cls._registry[channel_type] = channel_class
        logger.info(f"Registered channel type: {channel_type} -> {channel_class.__name__}")
    
    @classmethod
    def create_channel(cls, channel_type: str, config: Dict[str, Any]) -> BaseChannel:
        """
        Create a channel instance by type.
        
        Args:
            channel_type: The type of channel to create
            config: Configuration dictionary for the channel
            
        Returns:
            An instance of the requested channel
            
        Raises:
            ChannelNotFoundError: If channel type is not registered
        """
        if channel_type not in cls._registry:
            raise ChannelNotFoundError(f"Channel type not found: {channel_type}")
            
        try:
            channel_class = cls._registry[channel_type]
            logger.debug(f"Creating channel instance: {channel_type}")
            return channel_class(config)
        except Exception as e:
            logger.error(f"Failed to create channel instance: {str(e)}")
            raise
    
    @classmethod
    def get_channel_types(cls) -> List[str]:
        """
        Get a list of all registered channel types.
        
        Returns:
            List of registered channel type names
        """
        return list(cls._registry.keys())
        
    @classmethod
    def get_channel_config(cls, channel_type: str) -> Dict[str, Any]:
        """
        Get configuration schema for a channel type.
        
        This method returns the configuration schema for a specific channel type,
        which can be used to validate channel configurations.
        
        Args:
            channel_type: The channel type to get configuration schema for
            
        Returns:
            Configuration schema for the channel type
            
        Raises:
            ChannelNotFoundError: If channel type is not registered
        """
        if channel_type not in cls._registry:
            raise ChannelNotFoundError(f"Channel type not found: {channel_type}")
            
        channel_class = cls._registry[channel_type]
        
        # If the channel class has a CONFIG_SCHEMA class attribute, return it
        if hasattr(channel_class, 'CONFIG_SCHEMA'):
            return channel_class.CONFIG_SCHEMA
            
        # Otherwise, try to infer from the channel's __init__ method
        try:
            signature = inspect.signature(channel_class.__init__)
            params = signature.parameters
            
            # Look for 'config' parameter annotations or defaults
            if 'config' in params and params['config'].annotation != inspect.Parameter.empty:
                return {
                    "type": str(params['config'].annotation),
                    "description": "Channel configuration"
                }
            
            return {
                "type": "dict",
                "description": "Channel configuration dictionary"
            }
        except Exception as e:
            logger.warning(f"Failed to get config schema for {channel_type}: {str(e)}")
            return {
                "type": "dict",
                "description": "Channel configuration dictionary"
            }
    
    @classmethod
    def _discover_channels(cls, package_path: str = "app.channels") -> None:
        """
        Automatically discover and register channel implementations.
        
        This method scans the specified package for channel implementations
        and registers them with the factory.
        
        Args:
            package_path: Module path to scan for channel implementations
        """
        try:
            package = importlib.import_module(package_path)
            
            # Get the package directory
            package_dir = getattr(package, '__path__', [None])[0]
            if not package_dir:
                logger.warning(f"Could not determine package directory for {package_path}")
                return
                
            # Look through all modules in the package
            for _, name, is_pkg in importlib.util.iter_modules([package_dir]):
                # Skip __init__.py and base.py
                if name in ['__init__', 'base', 'channel_factory']:
                    continue
                    
                if is_pkg:
                    # Recursively scan subpackages
                    cls._discover_channels(f"{package_path}.{name}")
                else:
                    try:
                        # Import the module
                        module = importlib.import_module(f"{package_path}.{name}")
                        
                        # Look for classes that extend BaseChannel
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            
                            if (inspect.isclass(attr) and 
                                issubclass(attr, BaseChannel) and 
                                attr != BaseChannel):
                                
                                # Generate a sensible channel type name
                                channel_type = attr_name.lower()
                                if channel_type.endswith('channel'):
                                    channel_type = channel_type[:-7]  # Remove 'channel' suffix
                                    
                                cls.register_channel(channel_type, attr)
                    except Exception as e:
                        logger.warning(f"Error discovering channels in {name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error during channel discovery: {str(e)}")
    
    @classmethod
    def initialize(cls) -> None:
        """
        Initialize the channel factory.
        
        This method should be called during application startup to discover
        and register all available channel implementations.
        """
        logger.info("Initializing ChannelFactory")
        cls._discover_channels()
        logger.info(f"Registered channel types: {cls.get_channel_types()}")