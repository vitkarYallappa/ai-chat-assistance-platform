from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class AuthType(str, Enum):
    """Enum defining supported authentication types."""
    NONE = "none"
    API_KEY = "api_key"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    OAUTH1 = "oauth1"
    JWT = "jwt"
    CUSTOM = "custom"


class HttpMethod(str, Enum):
    """Enum defining supported HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class RequestConfig:
    """Configuration for API requests including retry and timeout settings."""
    
    def __init__(
        self, 
        max_retries: int = 3, 
        timeout: int = 30,
        backoff_factor: float = 0.5,
        retry_status_codes: List[int] = None,
        retry_on_timeout: bool = True,
        verify_ssl: bool = True
    ):
        """
        Initialize RequestConfig with retry and timeout settings.
        
        Args:
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            backoff_factor: Backoff factor for exponential retry delay
            retry_status_codes: List of HTTP status codes to retry on
            retry_on_timeout: Whether to retry on timeout
            verify_ssl: Whether to verify SSL certificates
        """
        self.max_retries = max_retries
        self.timeout = timeout
        self.backoff_factor = backoff_factor
        self.retry_status_codes = retry_status_codes or [429, 500, 502, 503, 504]
        self.retry_on_timeout = retry_on_timeout
        self.verify_ssl = verify_ssl


class APIConnector(ABC):
    """
    Abstract base interface for API connectors.
    
    This interface defines the standard contract for components that handle 
    communication with external APIs, including authentication, request handling,
    rate limiting, and error processing.
    """
    
    @abstractmethod
    async def authenticate(self, auth_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles API authentication and returns credentials.
        
        Args:
            auth_config: Authentication configuration including credentials
                        and auth type.
                        
        Returns:
            Dict[str, Any]: Authentication details (e.g., token, expiry) to be
                          used in subsequent requests.
                          
        Raises:
            IntegrationException: If authentication fails.
        """
        pass
    
    @abstractmethod
    async def request(
        self,
        method: HttpMethod,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Dict[str, Any]] = None,
        config: Optional[RequestConfig] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Makes an HTTP request with retry logic.
        
        Args:
            method: HTTP method to use
            url: URL to make the request to
            params: Optional query parameters
            data: Optional request data/body
            headers: Optional request headers
            auth: Optional authentication details
            config: Optional request configuration
            **kwargs: Additional parameters to pass to the underlying HTTP library
            
        Returns:
            Dict[str, Any]: Response data from the API
            
        Raises:
            IntegrationException: If the request fails after retries
        """
        pass
    
    @abstractmethod
    async def handle_rate_limits(
        self, 
        response: Dict[str, Any], 
        retry_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Implements rate limiting handling logic.
        
        Args:
            response: The API response to check for rate limit headers
            retry_callback: Optional callback to execute before retrying
            
        Returns:
            Dict[str, Any]: The original or retried response
            
        Raises:
            IntegrationException: If rate limit is exceeded and cannot be handled
        """
        pass
    
    @abstractmethod
    async def handle_errors(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes error responses from the API.
        
        Args:
            response: The API response to process
            
        Returns:
            Dict[str, Any]: The processed response
            
        Raises:
            IntegrationException: If the response contains an error that cannot be handled
        """
        pass
    
    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """
        Validates that a URL is properly formatted and allowed.
        
        Args:
            url: The URL to validate
            
        Returns:
            bool: True if the URL is valid, False otherwise
        """
        # Default implementation
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception as e:
            logger.error(f"URL validation error: {str(e)}")
            return False
    
    @abstractmethod
    async def build_url(self, base_url: str, path: str, version: Optional[str] = None) -> str:
        """
        Builds a complete URL from components.
        
        Args:
            base_url: The base URL of the API
            path: The path to the specific resource
            version: Optional API version string
            
        Returns:
            str: The complete URL
        """
        # Default implementation
        url = base_url.rstrip('/')
        if version:
            url += f"/{version.strip('/')}"
        url += f"/{path.lstrip('/')}"
        return url