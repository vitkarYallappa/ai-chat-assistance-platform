from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Type variables for generics
T = TypeVar('T')  # Generic type for request data
R = TypeVar('R')  # Generic type for response data


class FallbackStrategy(str, Enum):
    """Enum defining fallback strategies when an API call fails."""
    CACHED = "cached"           # Return cached data
    DEFAULT = "default"         # Return default values
    ERROR = "error"             # Return error response
    ALTERNATIVE_API = "alternative_api"  # Try an alternative API
    DEGRADED = "degraded"       # Return partial data
    RETRY = "retry"             # Retry the request


class FallbackHandler(Generic[T, R], ABC):
    """
    Abstract base interface for fallback handlers.
    
    This interface defines the standard contract for components that provide
    fallback mechanisms when API calls fail.
    
    Type Parameters:
        T: The type of request data
        R: The type of response data
    """
    
    @abstractmethod
    async def handle_fallback(
        self, 
        request_data: T, 
        error: Exception, 
        strategy: FallbackStrategy = FallbackStrategy.CACHED
    ) -> R:
        """
        Handles fallback when an API call fails.
        
        Args:
            request_data: The original request data
            error: The exception that occurred
            strategy: The fallback strategy to use
            
        Returns:
            R: The fallback response data
            
        Raises:
            IntegrationException: If fallback handling fails
        """
        pass
    
    @abstractmethod
    async def get_cached_fallback(self, request_data: T) -> Optional[R]:
        """
        Retrieves cached data for fallback.
        
        Args:
            request_data: The original request data
            
        Returns:
            Optional[R]: The cached data if available, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_default_fallback(self, request_data: T) -> R:
        """
        Generates default data for fallback.
        
        Args:
            request_data: The original request data
            
        Returns:
            R: Default data for fallback
        """
        pass
    
    @abstractmethod
    async def try_alternative_api(self, request_data: T) -> Optional[R]:
        """
        Tries an alternative API as fallback.
        
        Args:
            request_data: The original request data
            
        Returns:
            Optional[R]: Data from alternative API if successful, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_degraded_response(self, request_data: T, partial_data: Optional[Any] = None) -> R:
        """
        Generates a degraded response with partial data.
        
        Args:
            request_data: The original request data
            partial_data: Optional partial data that was retrieved
            
        Returns:
            R: Degraded response with available data
        """
        pass
    
    @abstractmethod
    def is_retirable_error(self, error: Exception) -> bool:
        """
        Checks if an error is retirable.
        
        Args:
            error: The exception to check
            
        Returns:
            bool: True if the error is retirable, False otherwise
        """
        pass
    
    @abstractmethod
    def select_fallback_strategy(self, error: Exception) -> FallbackStrategy:
        """
        Selects an appropriate fallback strategy based on the error.
        
        Args:
            error: The exception that occurred
            
        Returns:
            FallbackStrategy: The selected fallback strategy
        """
        pass