import logging
from typing import Dict, Type, List, Optional

from app.adapters.interfaces.external_api import ExternalAPIAdaptorInterface

logger = logging.getLogger(__name__)

class AdaptorRegistry:
    """
    Registry of available adaptor implementations.
    Maps adaptor type strings to their implementing classes.
    Uses the Registry pattern to manage and access adaptor implementations.
    """
    
    def __init__(self):
        """
        Initialize an empty adaptor registry.
        """
        self._adaptors: Dict[str, Type[ExternalAPIAdaptorInterface]] = {}
        logger.debug("Initialized AdaptorRegistry")
    
    def register(self, adaptor_type: str, adaptor_class: Type[ExternalAPIAdaptorInterface]) -> None:
        """
        Register an adaptor implementation.
        
        Args:
            adaptor_type: Type identifier for the adaptor
            adaptor_class: Class to instantiate for this adaptor type
            
        Raises:
            ValueError: If the adaptor_type is invalid or already registered
        """
        # Validate adaptor type
        if not adaptor_type or not isinstance(adaptor_type, str):
            raise ValueError("Adaptor type must be a non-empty string")
        
        # Validate adaptor class
        if not isinstance(adaptor_class, type) or not issubclass(adaptor_class, ExternalAPIAdaptorInterface):
            raise ValueError(
                "Adaptor class must be a subclass of ExternalAPIAdaptorInterface"
            )
        
        # Check if already registered
        if adaptor_type in self._adaptors:
            raise ValueError(f"Adaptor type '{adaptor_type}' is already registered")
        
        # Register the adaptor
        self._adaptors[adaptor_type] = adaptor_class
        logger.info(f"Registered adaptor type: {adaptor_type}")
    
    def get(self, adaptor_type: str) -> Optional[Type[ExternalAPIAdaptorInterface]]:
        """
        Retrieve an adaptor implementation by type.
        
        Args:
            adaptor_type: Type identifier for the adaptor
            
        Returns:
            The adaptor class if found, None otherwise
        """
        return self._adaptors.get(adaptor_type)
    
    def list(self) -> List[str]:
        """
        List all registered adaptor types.
        
        Returns:
            List of registered adaptor type strings
        """
        return list(self._adaptors.keys())
    
    def is_registered(self, adaptor_type: str) -> bool:
        """
        Check if an adaptor type is registered.
        
        Args:
            adaptor_type: Type identifier for the adaptor
            
        Returns:
            True if registered, False otherwise
        """
        return adaptor_type in self._adaptors
    
    def clear(self) -> None:
        """
        Clear all registered adaptors.
        Primarily used for testing purposes.
        """
        self._adaptors.clear()
        logger.debug("Cleared all registered adaptors")