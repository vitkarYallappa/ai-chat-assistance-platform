"""
Fallback mechanism for the Adaptor Service.
Provides strategies to handle API failures gracefully.
"""
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Callable
import logging
from datetime import datetime, timedelta
import json

from pydantic import BaseModel

from app.infrastructure.error.handler import ErrorDetails, ErrorCategory
from app.adapters.interfaces.fallback import FallbackStrategy


# Generic type for fallback data
T = TypeVar('T')


class FallbackMetadata(BaseModel):
    """Metadata for fallback entries to track freshness and validity."""
    source: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_stale: bool = False
    error_context: Optional[Dict[str, Any]] = None


class FallbackEntry(Generic[T], BaseModel):
    """A fallback data entry with its metadata."""
    data: T
    metadata: FallbackMetadata
    
    class Config:
        arbitrary_types_allowed = True


class FallbackRegistry(BaseModel):
    """Registry for available fallback strategies."""
    operation_key: str
    strategies: List[FallbackStrategy]
    
    class Config:
        arbitrary_types_allowed = True


class FallbackHandler:
    """
    Manages fallback mechanisms for graceful degradation 
    when external APIs fail.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize the fallback handler.
        
        Args:
            logger: Logger instance for fallback operations
        """
        self.logger = logger
        self._registry: Dict[str, FallbackRegistry] = {}
        
    def register_fallback(
        self, 
        operation_key: str, 
        strategy: FallbackStrategy
    ) -> None:
        """
        Register a fallback strategy for a specific operation.
        
        Args:
            operation_key: Unique identifier for the operation
            strategy: Fallback strategy implementation
        """
        if operation_key not in self._registry:
            self._registry[operation_key] = FallbackRegistry(
                operation_key=operation_key,
                strategies=[]
            )
            
        # Ensure we don't register the same strategy twice
        if strategy not in self._registry[operation_key].strategies:
            # Add strategy to registry, maintaining priority order (highest first)
            strategies = self._registry[operation_key].strategies
            strategies.append(strategy)
            strategies.sort(key=lambda s: s.get_fallback_priority(), reverse=True)
            
            self.logger.info(
                f"Registered fallback strategy for operation '{operation_key}': "
                f"{strategy.__class__.__name__} with priority {strategy.get_fallback_priority()}"
            )
    
    def has_fallback(self, operation_key: str, request_params: Dict[str, Any] = None) -> bool:
        """
        Check if a fallback exists for an operation.
        
        Args:
            operation_key: Unique identifier for the operation
            request_params: Parameters for the operation
            
        Returns:
            bool: True if a fallback is available, False otherwise
        """
        if request_params is None:
            request_params = {}
            
        # Check if we have any strategies registered for this operation
        if operation_key not in self._registry:
            return False
            
        # Check if any registered strategy can handle this request
        for strategy in self._registry[operation_key].strategies:
            if strategy.can_handle(request_params):
                return True
                
        return False
        
    def execute_fallback(
        self, 
        operation_key: str, 
        request_params: Dict[str, Any],
        error_details: ErrorDetails
    ) -> Any:
        """
        Execute the appropriate fallback strategy for an operation.
        
        Args:
            operation_key: Unique identifier for the operation
            request_params: Parameters for the operation
            error_details: Details about the error that triggered the fallback
            
        Returns:
            Any: Fallback data
            
        Raises:
            ValueError: If no suitable fallback is available
        """
        if operation_key not in self._registry:
            raise ValueError(f"No fallback strategies registered for operation '{operation_key}'")
            
        # Try each strategy in priority order
        for strategy in self._registry[operation_key].strategies:
            if strategy.can_handle(request_params):
                self.logger.info(
                    f"Executing fallback strategy {strategy.__class__.__name__} "
                    f"for operation '{operation_key}'"
                )
                
                try:
                    result = strategy.execute(request_params, error_details)
                    
                    self.logger.info(
                        f"Fallback strategy {strategy.__class__.__name__} "
                        f"successfully executed for operation '{operation_key}'"
                    )
                    
                    return result
                except Exception as e:
                    self.logger.warning(
                        f"Fallback strategy {strategy.__class__.__name__} failed: {str(e)}. "
                        f"Trying next strategy if available."
                    )
        
        # If we reach here, no strategy was successful
        raise ValueError(
            f"No suitable fallback strategy available for operation '{operation_key}' "
            f"with params {json.dumps(request_params, default=str)}"
        )
    
    def get_fallback_data(
        self, 
        operation_key: str, 
        request_params: Dict[str, Any],
        error_details: ErrorDetails
    ) -> Any:
        """
        Gets fallback data when an API operation fails.
        
        Args:
            operation_key: Unique identifier for the operation
            request_params: Parameters for the original operation
            error_details: Details about the error that triggered the fallback
            
        Returns:
            Any: Fallback data
            
        Raises:
            ValueError: If no suitable fallback is available
        """
        return self.execute_fallback(operation_key, request_params, error_details)