import logging
from typing import Dict, Any, Optional, Type, List

from app.core.exceptions import AdaptorConfigError, AdaptorNotFoundError
from app.adapters.interfaces.external_api import ExternalAPIAdaptorInterface
from app.adapters.registry import AdaptorRegistry

logger = logging.getLogger(__name__)

class AdaptorFactory:
    """
    Factory for creating adaptor instances.
    Uses a registry to instantiate the appropriate adaptor based on type.
    Follows the Factory Method pattern for creating objects.
    """
    
    def __init__(self, registry: AdaptorRegistry = None):
        """
        Initialize the adaptor factory with an optional registry.
        
        Args:
            registry: Optional registry of available adaptors
        """
        self.registry = registry or AdaptorRegistry()
        logger.info("Initialized AdaptorFactory")
    
    async def create_adaptor(self, adaptor_type: str, config: Dict[str, Any]) -> ExternalAPIAdaptorInterface:
        """
        Create an adaptor instance of the specified type with the given configuration.
        
        Args:
            adaptor_type: Type of adaptor to create (e.g., 'shopify', 'woocommerce')
            config: Configuration for the adaptor
            
        Returns:
            An instance of the requested adaptor
            
        Raises:
            AdaptorNotFoundError: If the adaptor type is not registered
            AdaptorConfigError: If the configuration is invalid
        """
        try:
            # Get the adaptor class from the registry
            adaptor_class = self.registry.get(adaptor_type)
            
            if not adaptor_class:
                raise AdaptorNotFoundError(f"Adaptor type '{adaptor_type}' not found in registry")
            
            # Validate required configuration
            tenant_id = config.get("tenant_id")
            if not tenant_id:
                raise AdaptorConfigError("Tenant ID is required in adaptor configuration")
            
            # Create an instance of the adaptor
            adaptor = adaptor_class(config)
            
            # If cache is provided in config, set it
            if "cache" in config:
                adaptor.set_cache(config["cache"])
            
            logger.info(f"Created {adaptor_type} adaptor for tenant {tenant_id}")
            return adaptor
            
        except AdaptorNotFoundError:
            logger.error(f"Adaptor type '{adaptor_type}' not found in registry")
            raise
            
        except AdaptorConfigError as e:
            logger.error(f"Invalid configuration for {adaptor_type} adaptor: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Error creating {adaptor_type} adaptor: {str(e)}")
            raise AdaptorConfigError(f"Failed to create {adaptor_type} adaptor: {str(e)}")
    
    def register_adaptor(self, adaptor_type: str, adaptor_class: Type[ExternalAPIAdaptorInterface]) -> None:
        """
        Register a new adaptor implementation with the factory.
        
        Args:
            adaptor_type: Type identifier for the adaptor
            adaptor_class: Class to instantiate for this adaptor type
        """
        self.registry.register(adaptor_type, adaptor_class)
        logger.info(f"Registered adaptor type: {adaptor_type}")
    
    def get_adaptor_types(self) -> List[str]:
        """
        List all available adaptor types.
        
        Returns:
            List of registered adaptor type strings
        """
        return self.registry.list()
    
    def get_adaptor_config_schema(self, adaptor_type: str) -> Dict[str, Any]:
        """
        Get the configuration schema for an adaptor type.
        
        Args:
            adaptor_type: Type of adaptor to get schema for
            
        Returns:
            Dictionary describing configuration requirements
            
        Raises:
            AdaptorNotFoundError: If the adaptor type is not registered
        """
        adaptor_class = self.registry.get(adaptor_type)
        
        if not adaptor_class:
            raise AdaptorNotFoundError(f"Adaptor type '{adaptor_type}' not found in registry")
        
        # Check if the adaptor class has a CONFIG_SCHEMA attribute
        if hasattr(adaptor_class, "CONFIG_SCHEMA"):
            return adaptor_class.CONFIG_SCHEMA
        
        # Default schema with common fields
        return {
            "tenant_id": {
                "type": "string",
                "required": True,
                "description": "Tenant ID for the adaptor"
            },
            "cache_enabled": {
                "type": "boolean",
                "required": False,
                "default": True,
                "description": "Whether to enable caching for this adaptor"
            },
            "cache_ttl": {
                "type": "integer",
                "required": False,
                "default": 300,
                "description": "Cache TTL in seconds"
            }
        }