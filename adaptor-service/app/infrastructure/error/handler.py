"""
Error handling module for the Adaptor Service.
Provides centralized error processing and categorization.
"""
import logging
from typing import Any, Dict, Optional, Union, List, Callable
from enum import Enum
import traceback
from datetime import datetime

from pydantic import BaseModel
from fastapi import status

# Import custom exception types
from app.core.exceptions import (
    ExternalAPIError,
    RateLimitError,
    AuthenticationError,
    ConnectionError,
    TimeoutError,
    ValidationError,
    ResourceNotFoundError,
    InternalError,
)


class ErrorCategory(str, Enum):
    """Categorization of errors for processing and reporting."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    RESOURCE_NOT_FOUND = "resource_not_found"
    EXTERNAL_API = "external_api"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


class ErrorSeverity(str, Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorDetails(BaseModel):
    """Structured error details for consistency in logging and reporting."""
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    source: str
    error_code: Optional[str] = None
    http_status_code: Optional[int] = None
    context: Dict[str, Any] = {}
    stacktrace: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 0
    should_notify: bool = False


class ErrorHandler:
    """
    Central error processing class that handles error categorization,
    logging, notification, and retry decisions.
    """

    def __init__(
        self,
        logger: logging.Logger,
        notify_callback: Optional[Callable[[ErrorDetails], None]] = None,
        default_max_retries: int = 3
    ):
        """
        Initialize the error handler.
        
        Args:
            logger: Logger instance for error logging
            notify_callback: Optional callback function for error notifications
            default_max_retries: Default maximum number of retries for retryable errors
        """
        self.logger = logger
        self.notify_callback = notify_callback
        self.default_max_retries = default_max_retries
        
        # Map exceptions to categories and severities
        self.exception_map = {
            AuthenticationError: (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH),
            RateLimitError: (ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM),
            ConnectionError: (ErrorCategory.CONNECTION, ErrorSeverity.MEDIUM),
            TimeoutError: (ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM),
            ValidationError: (ErrorCategory.VALIDATION, ErrorSeverity.LOW),
            ResourceNotFoundError: (ErrorCategory.RESOURCE_NOT_FOUND, ErrorSeverity.MEDIUM),
            ExternalAPIError: (ErrorCategory.EXTERNAL_API, ErrorSeverity.HIGH),
            InternalError: (ErrorCategory.INTERNAL, ErrorSeverity.HIGH),
        }
        
        # Define which error categories are retryable
        self.retryable_categories = {
            ErrorCategory.CONNECTION,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RATE_LIMIT,
        }
        
        # Define critical errors that should always trigger notification
        self.critical_notification_categories = {
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.INTERNAL,
        }

    def handle_error(
        self,
        exception: Exception,
        source: str,
        context: Dict[str, Any] = None,
        retry_count: int = 0,
        max_retries: Optional[int] = None,
    ) -> ErrorDetails:
        """
        Process an error, logging and determining retry strategy.
        
        Args:
            exception: The exception that occurred
            source: Source identifier (e.g., "shopify_adapter", "workday_connector")
            context: Additional context about the error
            retry_count: Current retry attempt number
            max_retries: Maximum number of retries allowed, defaults to handler default
            
        Returns:
            ErrorDetails: Structured details about the error
        """
        if context is None:
            context = {}
            
        # Set default max retries if not provided
        if max_retries is None:
            max_retries = self.default_max_retries
        
        # Categorize the error
        error_details = self.categorize_error(
            exception=exception,
            source=source,
            context=context,
            retry_count=retry_count,
            max_retries=max_retries
        )
        
        # Log the error
        self.log_error(error_details)
        
        # Check if notification is required
        if self.should_notify(error_details):
            error_details.should_notify = True
            self.notify_error(error_details)
            
        return error_details

    def categorize_error(
        self,
        exception: Exception,
        source: str,
        context: Dict[str, Any],
        retry_count: int = 0,
        max_retries: int = 3,
    ) -> ErrorDetails:
        """
        Categorize an error based on the exception type and build error details.
        
        Args:
            exception: The exception that occurred
            source: Source identifier
            context: Additional context about the error
            retry_count: Current retry attempt number
            max_retries: Maximum number of retries allowed
            
        Returns:
            ErrorDetails: Structured details about the error
        """
        # Get exception type for mapping
        exception_type = type(exception)
        
        # Default category and severity
        category = ErrorCategory.UNKNOWN
        severity = ErrorSeverity.MEDIUM
        
        # Map exception to category and severity if in our map
        if exception_type in self.exception_map:
            category, severity = self.exception_map[exception_type]
        
        # Handle specific external API errors with more detail
        http_status_code = None
        error_code = None
        
        if hasattr(exception, "status_code"):
            http_status_code = getattr(exception, "status_code")
            
            # Adjust severity based on HTTP status code
            if http_status_code >= 500:
                severity = ErrorSeverity.HIGH
            elif http_status_code == 429:
                category = ErrorCategory.RATE_LIMIT
                severity = ErrorSeverity.MEDIUM
            elif http_status_code in (401, 403):
                category = ErrorCategory.AUTHENTICATION
                severity = ErrorSeverity.HIGH
            elif http_status_code == 404:
                category = ErrorCategory.RESOURCE_NOT_FOUND
                severity = ErrorSeverity.MEDIUM
                
        if hasattr(exception, "error_code"):
            error_code = getattr(exception, "error_code")
        
        # Create detailed error information
        error_details = ErrorDetails(
            timestamp=datetime.utcnow(),
            category=category,
            severity=severity,
            message=str(exception),
            source=source,
            error_code=error_code,
            http_status_code=http_status_code,
            context=context,
            retry_count=retry_count,
            max_retries=max_retries,
            stacktrace=traceback.format_exc(),
        )
        
        return error_details

    def should_retry(self, error_details: ErrorDetails) -> bool:
        """
        Determine if an operation should be retried based on error details.
        
        Args:
            error_details: Structured error information
            
        Returns:
            bool: True if the operation should be retried, False otherwise
        """
        # Don't retry if we've exceeded max retries
        if error_details.retry_count >= error_details.max_retries:
            return False
        
        # Only retry if the error category is in our retryable list
        return error_details.category in self.retryable_categories

    def should_notify(self, error_details: ErrorDetails) -> bool:
        """
        Determine if an error should trigger notifications.
        
        Args:
            error_details: Structured error information
            
        Returns:
            bool: True if notifications should be sent, False otherwise
        """
        # Always notify for critical errors
        if error_details.severity == ErrorSeverity.CRITICAL:
            return True
            
        # Notify for high severity errors
        if error_details.severity == ErrorSeverity.HIGH:
            return True
            
        # Always notify for specific categories regardless of severity
        if error_details.category in self.critical_notification_categories:
            return True
            
        # Notify for persistent retryable errors
        if (error_details.category in self.retryable_categories and 
                error_details.retry_count >= error_details.max_retries):
            return True
            
        return False

    def log_error(self, error_details: ErrorDetails) -> None:
        """
        Log error details at the appropriate level.
        
        Args:
            error_details: Structured error information
        """
        # Prepare log data
        log_data = {
            "timestamp": error_details.timestamp.isoformat(),
            "category": error_details.category,
            "severity": error_details.severity,
            "source": error_details.source,
            "message": error_details.message,
            "retry_count": error_details.retry_count,
            "max_retries": error_details.max_retries,
        }
        
        # Add optional fields if present
        if error_details.error_code:
            log_data["error_code"] = error_details.error_code
            
        if error_details.http_status_code:
            log_data["http_status_code"] = error_details.http_status_code
            
        if error_details.context:
            log_data["context"] = error_details.context
        
        # Choose log level based on severity
        if error_details.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"CRITICAL ERROR: {error_details.message}", extra=log_data)
            # Also log stacktrace for critical errors
            if error_details.stacktrace:
                self.logger.critical(f"Stacktrace:\n{error_details.stacktrace}")
                
        elif error_details.severity == ErrorSeverity.HIGH:
            self.logger.error(f"ERROR: {error_details.message}", extra=log_data)
            # Also log stacktrace for high severity errors
            if error_details.stacktrace:
                self.logger.error(f"Stacktrace:\n{error_details.stacktrace}")
                
        elif error_details.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"WARNING: {error_details.message}", extra=log_data)
            
        else:  # LOW severity
            self.logger.info(f"INFO: {error_details.message}", extra=log_data)

    def notify_error(self, error_details: ErrorDetails) -> None:
        """
        Send error notifications via the configured callback.
        
        Args:
            error_details: Structured error information
        """
        if self.notify_callback:
            try:
                self.notify_callback(error_details)
            except Exception as e:
                # Log but don't raise if notification itself fails
                self.logger.error(
                    f"Failed to send error notification: {str(e)}",
                    extra={"error_details": error_details.dict()}
                )