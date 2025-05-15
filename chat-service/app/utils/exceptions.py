from typing import Any, Dict, Optional, Type
from fastapi import status


class AppException(Exception):
    """Base application exception class."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            status_code: HTTP status code to return
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AppException):
    """Exception for data validation errors."""
    
    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize validation exception.
        
        Args:
            message: Error message
            details: Validation error details
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class NotFoundException(AppException):
    """Exception for resource not found errors."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        message: Optional[str] = None
    ):
        """
        Initialize not found exception.
        
        Args:
            resource_type: Type of resource not found
            resource_id: ID of the resource
            message: Custom error message
        """
        super().__init__(
            message=message or f"{resource_type} with ID {resource_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class UnauthorizedException(AppException):
    """Exception for authentication errors."""
    
    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize unauthorized exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class ForbiddenException(AppException):
    """Exception for authorization errors."""
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize forbidden exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ExternalServiceException(AppException):
    """Exception for external service integration errors."""
    
    def __init__(
        self,
        service_name: str,
        message: str = "External service error",
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize external service exception.
        
        Args:
            service_name: Name of the external service
            message: Error message
            status_code: HTTP status code
            details: Additional error details
        """
        error_details = details or {}
        error_details["service"] = service_name
        
        super().__init__(
            message=message,
            status_code=status_code,
            details=error_details
        )