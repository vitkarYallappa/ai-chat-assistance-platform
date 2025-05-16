import base64
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import AuthenticationError, TokenRefreshError
from app.core.logging import get_logger

logger = get_logger(__name__)

class OAuthToken(BaseModel):
    """Model representing an OAuth token."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    expires_in: int
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

class OAuthHandler:
    """Handles OAuth authentication for external APIs."""
    
    def __init__(
        self, 
        client_id: str, 
        client_secret: str, 
        token_url: str,
        auth_url: Optional[str] = None,
        scope: Optional[str] = None,
        http_client: Optional[httpx.Client] = None
    ):
        """
        Initialize the OAuth handler.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            token_url: URL to obtain tokens
            auth_url: Authorization URL for OAuth flow
            scope: OAuth scope(s)
            http_client: Optional HTTP client for requests
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.auth_url = auth_url
        self.scope = scope
        self.http_client = http_client or httpx.Client(timeout=10.0)
        
        # Cache for tokens
        self._token_cache: Dict[str, OAuthToken] = {}
    
    async def get_token(
        self, 
        grant_type: str = "client_credentials", 
        cache_key: Optional[str] = None,
        **kwargs
    ) -> OAuthToken:
        """
        Obtain an OAuth token.
        
        Args:
            grant_type: OAuth grant type
            cache_key: Key for token caching
            **kwargs: Additional parameters for token request
            
        Returns:
            OAuth token
            
        Raises:
            AuthenticationError: If token acquisition fails
        """
        # Use cache if available and not expired
        cache_key = cache_key or f"{self.client_id}:{grant_type}"
        cached_token = self._token_cache.get(cache_key)
        if cached_token and not cached_token.is_expired():
            logger.debug(f"Using cached token for {cache_key}")
            return cached_token
            
        # Prepare token request
        data = {
            "grant_type": grant_type,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        # Add scope if present
        if self.scope:
            data["scope"] = self.scope
            
        # Add any additional parameters
        data.update(kwargs)
        
        try:
            # Make the token request
            response = await self.http_client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Raise for HTTP errors
            response.raise_for_status()
            
            # Parse token response
            token_data = response.json()
            
            # Calculate token expiration
            expires_in = token_data.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            token_data["expires_at"] = expires_at
            
            # Create token object
            token = OAuthToken(**token_data)
            
            # Cache the token
            self._token_cache[cache_key] = token
            
            logger.info(f"Successfully obtained OAuth token for {cache_key}")
            return token
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during token acquisition: {str(e)}")
            raise AuthenticationError(f"Failed to get OAuth token: {str(e)}")
        except httpx.RequestError as e:
            logger.error(f"Request error during token acquisition: {str(e)}")
            raise AuthenticationError(f"Failed to connect to token endpoint: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token acquisition: {str(e)}")
            raise AuthenticationError(f"Unexpected error during token acquisition: {str(e)}")
    
    async def refresh_token(self, refresh_token: str, cache_key: Optional[str] = None) -> OAuthToken:
        """
        Refresh an expired OAuth token.
        
        Args:
            refresh_token: Refresh token
            cache_key: Key for token caching
            
        Returns:
            New OAuth token
            
        Raises:
            TokenRefreshError: If token refresh fails
        """
        try:
            # Prepare refresh request
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            # Make the refresh request
            response = await self.http_client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Raise for HTTP errors
            response.raise_for_status()
            
            # Parse token response
            token_data = response.json()
            
            # Calculate token expiration
            expires_in = token_data.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            token_data["expires_at"] = expires_at
            
            # Create token object
            token = OAuthToken(**token_data)
            
            # Cache the token if cache_key provided
            if cache_key:
                self._token_cache[cache_key] = token
                
            logger.info(f"Successfully refreshed OAuth token for {cache_key or 'unknown client'}")
            return token
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during token refresh: {str(e)}")
            raise TokenRefreshError(f"Failed to refresh OAuth token: {str(e)}")
        except httpx.RequestError as e:
            logger.error(f"Request error during token refresh: {str(e)}")
            raise TokenRefreshError(f"Failed to connect to token endpoint: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            raise TokenRefreshError(f"Unexpected error during token refresh: {str(e)}")
    
    async def validate_token(self, token: str, introspection_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate an OAuth token.
        
        Args:
            token: Token to validate
            introspection_url: URL for token introspection
            
        Returns:
            Token validation information
            
        Raises:
            AuthenticationError: If token validation fails
        """
        if not introspection_url:
            # If no introspection URL, just check token format
            if not token or len(token.split('.')) != 3:
                raise AuthenticationError("Invalid token format")
            
            # Try to decode the token without verification
            try:
                parts = token.split('.')
                payload_part = parts[1]
                # Add padding if needed
                padding = len(payload_part) % 4
                if padding:
                    payload_part += '=' * (4 - padding)
                
                decoded = base64.b64decode(payload_part)
                payload = json.loads(decoded)
                
                # Check if token has expired
                exp = payload.get('exp')
                if exp and int(time.time()) > exp:
                    raise AuthenticationError("Token has expired")
                
                return payload
            except Exception as e:
                raise AuthenticationError(f"Token validation failed: {str(e)}")
        
        # If introspection URL is provided, use it
        try:
            # Prepare introspection request
            data = {
                "token": token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            # Make the introspection request
            response = await self.http_client.post(
                introspection_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Raise for HTTP errors
            response.raise_for_status()
            
            # Parse introspection response
            introspection_data = response.json()
            
            # Check if token is active
            if not introspection_data.get("active", False):
                raise AuthenticationError("Token is not active")
                
            logger.debug(f"Successfully validated token")
            return introspection_data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during token validation: {str(e)}")
            raise AuthenticationError(f"Failed to validate token: {str(e)}")
        except httpx.RequestError as e:
            logger.error(f"Request error during token validation: {str(e)}")
            raise AuthenticationError(f"Failed to connect to introspection endpoint: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            raise AuthenticationError(f"Unexpected error during token validation: {str(e)}")
    
    async def revoke_token(self, token: str, revocation_url: str, token_type_hint: str = "access_token") -> bool:
        """
        Revoke an OAuth token.
        
        Args:
            token: Token to revoke
            revocation_url: URL for token revocation
            token_type_hint: Type of token (access_token or refresh_token)
            
        Returns:
            True if token was revoked successfully
            
        Raises:
            AuthenticationError: If token revocation fails
        """
        try:
            # Prepare revocation request
            data = {
                "token": token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "token_type_hint": token_type_hint
            }
            
            # Make the revocation request
            response = await self.http_client.post(
                revocation_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Raise for HTTP errors
            response.raise_for_status()
            
            # Check if token was successfully revoked
            if response.status_code in (200, 204):
                logger.info(f"Successfully revoked token")
                return True
            
            return False
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during token revocation: {str(e)}")
            raise AuthenticationError(f"Failed to revoke token: {str(e)}")
        except httpx.RequestError as e:
            logger.error(f"Request error during token revocation: {str(e)}")
            raise AuthenticationError(f"Failed to connect to revocation endpoint: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token revocation: {str(e)}")
            raise AuthenticationError(f"Unexpected error during token revocation: {str(e)}")
    
    def build_authorization_url(
        self, 
        redirect_uri: str, 
        state: Optional[str] = None, 
        scope: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Build an authorization URL for OAuth flow.
        
        Args:
            redirect_uri: Redirect URI after authorization
            state: State parameter for CSRF protection
            scope: OAuth scope(s)
            **kwargs: Additional parameters for authorization URL
            
        Returns:
            Authorization URL
            
        Raises:
            ValueError: If auth_url is not provided
        """
        if not self.auth_url:
            raise ValueError("Authorization URL not provided")
            
        # Prepare authorization parameters
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code"
        }
        
        # Add state if provided
        if state:
            params["state"] = state
            
        # Add scope if provided
        effective_scope = scope or self.scope
        if effective_scope:
            params["scope"] = effective_scope
            
        # Add any additional parameters
        params.update(kwargs)
        
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        
        # Return authorization URL
        return f"{self.auth_url}?{query_string}"