from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union
from enum import Enum
import logging

logger = logging.getLogger(__name__)

from app.infrastructure.error.handler import ErrorDetails

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
    @abc.abstractmethod
    def execute(self, request_params: Dict[str, Any], error_details: ErrorDetails) -> T:
        """
        Execute the fallback strategy to retrieve alternative data.
        
        Args:
            request_params: Parameters from the original request
            error_details: Details about the error that triggered the fallback
            
        Returns:
            T: Fallback data of the appropriate type
            
        Raises:
            Exception: If the fallback strategy itself fails
        """
        pass
    
    @abc.abstractmethod
    def can_handle(self, request_params: Dict[str, Any]) -> bool:
        """
        Check if this strategy can handle the given request parameters.
        
        Args:
            request_params: Parameters from the original request
            
        Returns:
            bool: True if this strategy can handle the request, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def get_fallback_priority(self) -> int:
        """
        Get the priority of this fallback strategy.
        Higher values indicate higher priority.
        
        Returns:
            int: Priority value
        """
        pass
    
    
class CacheFallbackStrategy(FallbackStrategy[T], abc.ABC):
    """
    Abstract fallback strategy that retrieves data from cache.
    """
    
    def get_fallback_priority(self) -> int:
        """
        Cache-based fallbacks typically have high priority.
        
        Returns:
            int: Priority value (default: 100)
        """
        return 100


class StaticFallbackStrategy(FallbackStrategy[T], abc.ABC):
    """
    Abstract fallback strategy that returns static predefined data.
    """
    
    def get_fallback_priority(self) -> int:
        """
        Static fallbacks typically have lower priority than cache fallbacks.
        
        Returns:
            int: Priority value (default: 50)
        """
        return 50


class EmptyResponseFallbackStrategy(FallbackStrategy[T], abc.ABC):
    """
    Abstract fallback strategy that returns an empty or minimal response.
    """
    
    def get_fallback_priority(self) -> int:
        """
        Empty response fallbacks typically have lowest priority.
        
        Returns:
            int: Priority value (default: 10)
        """
        return 10


class CompositeFallbackStrategy(FallbackStrategy[T], abc.ABC):
    """
    Abstract fallback strategy that combines multiple strategies.
    """
    
    def __init__(self, strategies: Optional[list[FallbackStrategy[T]]] = None):
        """
        Initialize with a list of strategies.
        
        Args:
            strategies: List of fallback strategies to try in order
        """
        self.strategies = strategies or []
    
    def add_strategy(self, strategy: FallbackStrategy[T]) -> None:
        """
        Add a fallback strategy to the composite.
        
        Args:
            strategy: Fallback strategy to add
        """
        if strategy not in self.strategies:
            self.strategies.append(strategy)
    
    def execute(self, request_params: Dict[str, Any], error_details: ErrorDetails) -> T:
        """
        Try each strategy in sequence until one succeeds.
        
        Args:
            request_params: Parameters from the original request
            error_details: Details about the error that triggered the fallback
            
        Returns:
            T: Result from the first successful strategy
            
        Raises:
            Exception: If all strategies fail
        """
        last_error = None
        
        for strategy in self.strategies:
            if strategy.can_handle(request_params):
                try:
                    return strategy.execute(request_params, error_details)
                except Exception as e:
                    last_error = e
        
        if last_error:
            raise last_error
        else:
            raise ValueError("No suitable fallback strategy found")