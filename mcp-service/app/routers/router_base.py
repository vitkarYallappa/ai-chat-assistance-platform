from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.utils.logger import get_logger
from app.domain.models.message import Message
from app.utils.exceptions import RoutingError, ValidationError


class RouterBase(ABC):
    """
    Base router class that defines the interface for all router implementations.
    Responsible for routing messages between different system components.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the router with configuration.
        
        Args:
            config: Optional configuration dictionary for the router
        """
        self.logger = get_logger(__name__)
        self.config = config or {}
        self.metrics = self._initialize_metrics()
    
    def _initialize_metrics(self):
        """
        Initialize metrics collection for the router.
        
        Returns:
            Metrics collector instance
        """
        # This would be implemented with your metrics library
        # For example, using Prometheus or a custom metrics collector
        try:
            from app.utils.metrics import MetricsCollector
            return MetricsCollector(prefix="router")
        except ImportError:
            self.logger.warning("Metrics collector not available")
            return None
    
    @abstractmethod
    def route(self, message: Message, destination: str) -> Dict[str, Any]:
        """
        Route a message to a destination.
        
        Args:
            message: The message to route
            destination: The destination to route to
            
        Returns:
            The response from the destination
            
        Raises:
            RoutingError: If the message cannot be routed
        """
        pass
    
    def validate_message(self, message: Message) -> bool:
        """
        Validate a message before routing.
        
        Args:
            message: The message to validate
            
        Returns:
            True if the message is valid, False otherwise
            
        Raises:
            ValidationError: If the message is invalid
        """
        if not message:
            raise ValidationError("Message cannot be None")
            
        if not message.id:
            raise ValidationError("Message must have an ID")
            
        if not message.content and not message.attachments:
            raise ValidationError("Message must have content or attachments")
            
        return True
    
    def handle_errors(self, error: Exception, message: Message) -> Dict[str, Any]:
        """
        Handle routing errors.
        
        Args:
            error: The error that occurred
            message: The message that was being routed
            
        Returns:
            An error response dictionary
        """
        self.logger.error(f"Error routing message {message.id}: {str(error)}", exc_info=True)
        
        if self.metrics:
            self.metrics.increment("routing_errors", {"error_type": type(error).__name__})
        
        # Create an error response
        error_response = {
            "success": False,
            "error": {
                "type": type(error).__name__,
                "message": str(error)
            },
            "message_id": message.id
        }
        
        return error_response
    
    def retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            error: The error to check
            
        Returns:
            True if the error is retryable, False otherwise
        """
        # Network and timeout errors are typically retryable
        retryable_errors = (
            "ConnectionError", 
            "Timeout", 
            "ServiceUnavailable",
            "TooManyRequests"
        )
        
        return type(error).__name__ in retryable_errors or any(
            err_type in str(error) for err_type in retryable_errors
        )