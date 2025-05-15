from typing import Any, Dict, List, Optional, TypeVar, Generic, Union
from enum import Enum
import logging

# Type variables for generics
T = TypeVar('T')  # Generic type for input data
R = TypeVar('R')  # Generic type for normalized/return data

logger = logging.getLogger(__name__)

class CapabilityType(str, Enum):
    """Enum defining types of capabilities an adaptor might support."""
    PRODUCTS = "products"
    INVENTORY = "inventory"
    ORDERS = "orders"
    CUSTOMERS = "customers"
    CATEGORIES = "categories"
    REAL_TIME = "real_time"
    BATCH = "batch"
    WEBHOOKS = "webhooks"


class APIStatus(str, Enum):
    """Enum defining possible API status values."""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ExternalAPIAdaptorInterface(Generic[T, R], ABC):
    """
    Abstract base interface for external API adaptors.
    
    This interface defines the standard contract that all external API adaptors
    must implement. It provides methods for connecting to APIs, fetching data,
    normalizing responses, checking availability, and reporting capabilities.
    
    Type Parameters:
        T: The type of data received from the external API
        R: The type of normalized data returned after processing
    """
    
    @abstractmethod
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Establishes a connection to the external API.
        
        Args:
            credentials: A dictionary containing authentication credentials
                        and connection parameters.
        
        Returns:
            bool: True if connection was successful, False otherwise.
            
        Raises:
            IntegrationException: If there is an error during connection.
        """
        pass
    
    @abstractmethod
    async def fetch(self, 
                   resource_type: str, 
                   query_params: Optional[Dict[str, Any]] = None, 
                   **kwargs) -> T:
        """
        Retrieves data from the external API.
        
        Args:
            resource_type: The type of resource to fetch (e.g., "products", "inventory").
            query_params: Optional query parameters to filter the results.
            **kwargs: Additional keyword arguments to customize the request.
            
        Returns:
            T: The raw data from the external API.
            
        Raises:
            IntegrationException: If there is an error during data retrieval.
            ValidationException: If the request parameters are invalid.
        """
        pass
    
    @abstractmethod
    async def normalize(self, data: T, target_schema: str = None) -> R:
        """
        Converts external API data to a standardized internal format.
        
        Args:
            data: The raw data from the external API.
            target_schema: Optional schema identifier to normalize to a specific format.
            
        Returns:
            R: The normalized data in the standardized format.
            
        Raises:
            ValidationException: If the data fails validation against the schema.
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> APIStatus:
        """
        Checks if the external API is available and functional.
        
        Returns:
            APIStatus: The current status of the API (AVAILABLE, DEGRADED, 
                      UNAVAILABLE, or UNKNOWN).
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Returns the capabilities supported by this adaptor.
        
        Returns:
            Dict[str, Any]: A dictionary of capabilities, including supported
                           resource types, operations, and performance characteristics.
        """
        pass
    
    @abstractmethod
    async def fetch_and_normalize(self, 
                                 resource_type: str,
                                 query_params: Optional[Dict[str, Any]] = None, 
                                 **kwargs) -> R:
        """
        Convenience method that fetches data and normalizes it in one operation.
        
        Args:
            resource_type: The type of resource to fetch.
            query_params: Optional query parameters to filter the results.
            **kwargs: Additional keyword arguments to customize the request.
            
        Returns:
            R: The normalized data in the standardized format.
            
        Raises:
            IntegrationException: If there is an error during data retrieval.
            ValidationException: If the request parameters are invalid or the
                               data fails validation.
        """
        # Default implementation, but concrete classes can override for optimization
        data = await self.fetch(resource_type, query_params, **kwargs)
        return await self.normalize(data)