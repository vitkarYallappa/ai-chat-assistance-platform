from fastapi import status
from typing import Any, Dict, Optional, Union


class APIException(Exception):
    """
    Base exception for API errors.
    
    All custom exceptions should inherit from this class.
    """
    
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An unexpected error occurred",
        code: str = "internal_error",
        context: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.context = context or {}
        super().__init__(self.detail)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to a dictionary for consistent response format."""
        return {
            "error": {
                "code": self.code,
                "message": self.detail,
                "status_code": self.status_code,
                "context": self.context
            }
        }


class IntegrationException(APIException):
    """Exception raised when an external API integration fails."""
    
    def __init__(
        self,
        detail: str = "External API integration error",
        code: str = "integration_error",
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(status_code=status_code, detail=detail, code=code, context=context)
        self.original_exception = original_exception
        
        # Add original exception info to context if available
        if original_exception and self.context is not None:
            self.context["original_error"] = str(original_exception)


class ValidationException(APIException):
    """Exception raised when data validation fails."""
    
    def __init__(
        self,
        detail: str = "Validation error",
        code: str = "validation_error",
        field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        merged_context = {"field": field} if field else {}
        if context:
            merged_context.update(context)
            
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            code=code,
            context=merged_context
        )


class NotFoundError(APIException):
    """Exception raised when a requested resource is not found."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Union[str, int],
        detail: Optional[str] = None,
        code: str = "not_found_error",
        context: Optional[Dict[str, Any]] = None
    ):
        if detail is None:
            detail = f"{resource_type} with id '{resource_id}' not found"
            
        merged_context = {
            "resource_type": resource_type,
            "resource_id": str(resource_id)
        }
        if context:
            merged_context.update(context)
            
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            code=code,
            context=merged_context
        )


class AuthenticationError(APIException):
    """Exception raised when authentication fails."""
    
    def __init__(
        self,
        detail: str = "Authentication failed",
        code: str = "authentication_error",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            code=code,
            context=context
        )


class AuthorizationError(APIException):
    """Exception raised when a user is not authorized to perform an action."""
    
    def __init__(
        self,
        detail: str = "Not authorized to perform this action",
        code: str = "authorization_error",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            code=code,
            context=context
        )


class RateLimitError(APIException):
    """Exception raised when rate limits are exceeded for external APIs."""
    
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        code: str = "rate_limit_error",
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        merged_context = {}
        if retry_after is not None:
            merged_context["retry_after"] = retry_after
            
        if context:
            merged_context.update(context)
            
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            code=code,
            context=merged_context
        )