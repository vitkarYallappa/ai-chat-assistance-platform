import json
import time
from typing import Any, Dict, List, Optional, Union
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from app.utils.exceptions import (
    APIConnectionError,
    APIResponseError,
    APIAuthenticationError,
    APIRateLimitError
)
from app.utils.logger import get_logger
from app.utils.retry import retry_with_backoff

logger = get_logger(__name__)

class WhatsAppClient:
    """
    Client for WhatsApp Business API.
    
    Handles communication with the WhatsApp Business API, including
    authentication, message sending, rate limiting, and error handling.
    """
    
    def __init__(
        self,
        base_url: str,
        api_version: str,
        phone_number_id: str,
        access_token: str,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize WhatsApp client.
        
        Args:
            base_url: Base URL for the WhatsApp API (usually graph.facebook.com)
            api_version: API version to use (e.g., 'v18.0')
            phone_number_id: WhatsApp phone number ID
            access_token: Access token for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for failed requests
        """
        self.base_url = base_url.rstrip('/')
        self.api_version = api_version
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Construct API endpoint base
        self.api_endpoint = f"{self.base_url}/{self.api_version}/{self.phone_number_id}"
        
        # Create session for connection pooling
        self.session = requests.Session()
        
        # Default headers for all requests
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        })
        
        logger.info(f"WhatsApp client initialized for phone number ID: {phone_number_id}")
    
    def authenticate(self) -> bool:
        """
        Verify authentication credentials.
        
        Returns:
            True if authentication is successful
            
        Raises:
            APIAuthenticationError: If authentication fails
        """
        try:
            # Make a lightweight call to verify credentials
            # This is simplified for the example - typically you'd use a proper endpoint
            response = self._make_request("GET", "/")
            return True
        except APIAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise APIAuthenticationError(f"Failed to authenticate: {str(e)}")
    
    @retry_with_backoff(
        retries=3,
        backoff_factor=2,
        retry_exceptions=(Timeout, ConnectionError, APIRateLimitError)
    )
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the WhatsApp API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to api_endpoint)
            data: Request body for POST/PUT requests
            params: URL parameters for GET requests
            
        Returns:
            Parsed JSON response
            
        Raises:
            APIConnectionError: If connection fails
            APIAuthenticationError: If authentication fails
            APIRateLimitError: If rate limit is exceeded
            APIResponseError: If API returns an error
        """
        url = f"{self.api_endpoint}{endpoint}"
        
        try:
            start_time = time.time()
            
            # Make the request
            response = self.session.request(
                method=method,
                url=url,
                json=data if data else None,
                params=params if params else None,
                timeout=self.timeout
            )
            
            # Log request duration
            duration = time.time() - start_time
            logger.debug(
                f"WhatsApp API request completed in {duration:.2f}s",
                extra={"url": url, "method": method, "status_code": response.status_code}
            )
            
            # Handle different response status codes
            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            
            # Parse error response
            error_info = self._parse_error_response(response)
            
            # Handle common error status codes
            if response.status_code == 401 or response.status_code == 403:
                raise APIAuthenticationError(
                    f"Authentication failed: {error_info.get('message', 'Unknown error')}"
                )
            elif response.status_code == 429:
                # Handle rate limiting
                retry_after = response.headers.get('Retry-After', 60)
                error_message = f"Rate limit exceeded. Retry after {retry_after} seconds."
                logger.warning(error_message)
                raise APIRateLimitError(error_message, retry_after=int(retry_after))
            else:
                # Handle other API errors
                error_message = error_info.get('message', f"API error: {response.status_code}")
                logger.error(
                    f"WhatsApp API error: {error_message}",
                    extra={"status_code": response.status_code, "error_info": error_info}
                )
                raise APIResponseError(error_message, status_code=response.status_code)
                
        except (Timeout, ConnectionError) as e:
            logger.error(f"WhatsApp API connection error: {str(e)}")
            raise APIConnectionError(f"Connection error: {str(e)}")
        except (APIAuthenticationError, APIRateLimitError, APIResponseError):
            # Re-raise these specific exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error in WhatsApp API request: {str(e)}")
            raise APIConnectionError(f"Request failed: {str(e)}")
    
    def _parse_error_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Parse error response from the WhatsApp API.
        
        Args:
            response: Response object from requests
            
        Returns:
            Dictionary containing error details
        """
        try:
            error_data = response.json()
            # Facebook Graph API typically returns errors in a specific format
            if 'error' in error_data:
                return error_data['error']
            return error_data
        except (ValueError, KeyError):
            return {"message": response.text or "Unknown error", "code": response.status_code}
    
    def send_text(self, recipient_id: str, text: str) -> Dict[str, Any]:
        """
        Send a text message via WhatsApp.
        
        Args:
            recipient_id: Recipient's WhatsApp ID
            text: Message content
            
        Returns:
            API response
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "text",
            "text": {
                "body": text
            }
        }
        
        logger.debug(f"Sending text message to {recipient_id}", extra={"text_length": len(text)})
        return self._make_request("POST", "/messages", data=payload)
    
    def send_template(
        self,
        recipient_id: str,
        template_name: str,
        template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a template message via WhatsApp.
        
        Args:
            recipient_id: Recipient's WhatsApp ID
            template_name: Name of the template
            template_data: Template parameters
            
        Returns:
            API response
        """
        # Prepare components based on template_data
        components = []
        
        # Add header component if present
        if "header" in template_data:
            header = template_data["header"]
            components.append({
                "type": "header",
                "parameters": [self._format_template_parameter(header)]
            })
        
        # Add body parameters if present
        if "body" in template_data:
            body_params = []
            if isinstance(template_data["body"], list):
                body_params = [
                    self._format_template_parameter(param) 
                    for param in template_data["body"]
                ]
            elif isinstance(template_data["body"], dict):
                body_params = [self._format_template_parameter(template_data["body"])]
                
            if body_params:
                components.append({
                    "type": "body",
                    "parameters": body_params
                })
        
        # Add buttons if present
        if "buttons" in template_data:
            buttons = template_data["buttons"]
            if buttons and isinstance(buttons, list):
                button_params = []
                for button in buttons:
                    button_params.append(self._format_template_parameter(button))
                    
                if button_params:
                    components.append({
                        "type": "button",
                        "sub_type": "quick_reply",
                        "index": "0",
                        "parameters": button_params
                    })
        
        # Prepare the payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": template_data.get("language", "en_US")
                },
                "components": components
            }
        }
        
        logger.debug(
            f"Sending template message to {recipient_id}",
            extra={"template_name": template_name}
        )
        return self._make_request("POST", "/messages", data=payload)
    
    def _format_template_parameter(self, param_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format parameter for a template message.
        
        Args:
            param_data: Parameter data
            
        Returns:
            Formatted parameter
        """
        param_type = param_data.get("type", "text")
        
        if param_type == "text":
            return {
                "type": "text",
                "text": param_data.get("text", "")
            }
        elif param_type == "image":
            return {
                "type": "image",
                "image": {
                    "link": param_data.get("link", "")
                }
            }
        elif param_type == "document":
            return {
                "type": "document",
                "document": {
                    "link": param_data.get("link", ""),
                    "filename": param_data.get("filename", "")
                }
            }
        elif param_type == "video":
            return {
                "type": "video",
                "video": {
                    "link": param_data.get("link", "")
                }
            }
        elif param_type == "location":
            return {
                "type": "location",
                "location": {
                    "latitude": param_data.get("latitude", 0),
                    "longitude": param_data.get("longitude", 0),
                    "name": param_data.get("name", ""),
                    "address": param_data.get("address", "")
                }
            }
        else:
            # Default to text
            return {
                "type": "text",
                "text": str(param_data.get("value", ""))
            }
    
    def send_media(
        self,
        recipient_id: str,
        media_type: str,
        media_url: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a media message via WhatsApp.
        
        Args:
            recipient_id: Recipient's WhatsApp ID
            media_type: Type of media (image, video, audio, document)
            media_url: URL of the media file
            caption: Optional caption for media
            
        Returns:
            API response
        """
        # Validate media type
        valid_media_types = ["image", "video", "audio", "document"]
        if media_type not in valid_media_types:
            raise ValueError(f"Invalid media type: {media_type}. Must be one of {valid_media_types}")
        
        # Build the media object
        media_object = {
            "link": media_url
        }
        
        # Add caption for supported media types
        if caption and media_type in ["image", "video", "document"]:
            media_object["caption"] = caption
        
        # Build the payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": media_type,
            media_type: media_object
        }
        
        logger.debug(
            f"Sending {media_type} message to {recipient_id}",
            extra={"media_url": media_url}
        )
        return self._make_request("POST", "/messages", data=payload)
    
    def send_interactive(
        self,
        recipient_id: str,
        interactive_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send an interactive message via WhatsApp.
        
        Args:
            recipient_id: Recipient's WhatsApp ID
            interactive_data: Interactive message data
            
        Returns:
            API response
        """
        # Validate interactive type
        interactive_type = interactive_data.get("type")
        valid_types = ["button", "list", "product", "product_list"]
        
        if not interactive_type or interactive_type not in valid_types:
            raise ValueError(f"Invalid interactive type: {interactive_type}. Must be one of {valid_types}")
        
        # Prepare payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "interactive",
            "interactive": interactive_data
        }
        
        logger.debug(
            f"Sending interactive message to {recipient_id}",
            extra={"interactive_type": interactive_type}
        )
        return self._make_request("POST", "/messages", data=payload)
    
    def __del__(self):
        """Clean up resources when object is destroyed."""
        if hasattr(self, 'session') and self.session:
            try:
                self.session.close()
            except Exception:
                pass