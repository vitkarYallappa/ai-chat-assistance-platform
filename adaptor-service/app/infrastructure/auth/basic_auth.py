import base64
import logging
from typing import Dict, Optional, Tuple

from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger

logger = get_logger(__name__)

class BasicAuthHandler:
    """Handles basic authentication for external APIs."""
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize the basic authentication handler.
        
        Args:
            username: Username for basic authentication
            password: Password for basic authentication
        """
        self.username = username
        self.password = password
    
    def generate_header(self, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, str]:
        """
        Generate an Authorization header for basic authentication.
        
        Args:
            username: Override instance username
            password: Override instance password
            
        Returns:
            Authorization header dict
            
        Raises:
            AuthenticationError: If credentials are missing
        """
        # Use provided credentials or fall back to instance variables
        effective_username = username or self.username
        effective_password = password or self.password
        
        # Validate credentials
        if not effective_username or not effective_password:
            logger.error("Missing credentials for basic authentication")
            raise AuthenticationError("Username and password are required for basic authentication")
            
        # Encode credentials
        encoded = self.encode_credentials(effective_username, effective_password)
        
        # Return header dict
        return {"Authorization": f"Basic {encoded}"}
    
    def validate_credentials(self, username: str, password: str, required_username: str, required_password: str) -> bool:
        """
        Validate basic auth credentials.
        
        Args:
            username: Provided username
            password: Provided password
            required_username: Required username
            required_password: Required password
            
        Returns:
            True if credentials are valid
        """
        return username == required_username and password == required_password
    
    @staticmethod
    def encode_credentials(username: str, password: str) -> str:
        """
        Encode credentials to base64 for basic authentication.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Base64 encoded credentials
        """
        # Combine username and password with colon
        credentials = f"{username}:{password}"
        
        # Encode to bytes
        credentials_bytes = credentials.encode("utf-8")
        
        # Encode to base64
        encoded_bytes = base64.b64encode(credentials_bytes)
        
        # Convert bytes to string
        return encoded_bytes.decode("utf-8")
    
    @staticmethod
    def decode_credentials(auth_header: str) -> Tuple[str, str]:
        """
        Decode base64 credentials from Authorization header.
        
        Args:
            auth_header: Authorization header value
            
        Returns:
            Tuple of (username, password)
            
        Raises:
            AuthenticationError: If header is invalid
        """
        try:
            # Check if header starts with "Basic "
            if not auth_header or not auth_header.startswith("Basic "):
                raise AuthenticationError("Invalid Authorization header format")
                
            # Extract encoded part
            encoded = auth_header[6:]  # Skip "Basic "
            
            # Decode from base64
            decoded_bytes = base64.b64decode(encoded)
            
            # Convert bytes to string
            decoded = decoded_bytes.decode("utf-8")
            
            # Split username and password
            parts = decoded.split(":", 1)
            if len(parts) != 2:
                raise AuthenticationError("Invalid credentials format")
                
            # Return username and password
            return parts[0], parts[1]
            
        except Exception as e:
            logger.error(f"Error decoding basic auth credentials: {str(e)}")
            raise AuthenticationError("Invalid basic authentication credentials")