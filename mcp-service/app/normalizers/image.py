"""
Image Message Normalizer Module.

This module implements the normalizer for image messages in the MCP Service.
The ImageNormalizer converts channel-specific image message formats to/from
the standardized internal format.
"""

import os
import re
import mimetypes
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

from app.domain.models.message import Message, MessageType
from app.normalizers.base import BaseNormalizer
from app.utils.logger import get_logger
from app.utils.exceptions import NormalizationError, ValidationError

logger = get_logger(__name__)

# Supported image mime types and extensions
SUPPORTED_IMAGE_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
    'image/webp', 'image/tiff', 'image/bmp'
}

SUPPORTED_IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff', '.bmp'
}


class ImageNormalizer(BaseNormalizer):
    """
    Normalizer for image messages across different channels.
    
    Converts channel-specific image message formats to/from the standardized
    internal message format.
    """
    
    def __init__(self, channel_id: str, tenant_id: str, 
                 max_size_kb: int = 10240,  # 10MB default max
                 allow_remote_urls: bool = True,
                 verify_mime_type: bool = True):
        """
        Initialize the image normalizer with configuration.
        
        Args:
            channel_id (str): The identifier for the messaging channel
            tenant_id (str): The identifier for the tenant
            max_size_kb (int): Maximum allowed image size in KB
            allow_remote_urls (bool): Whether to allow remote image URLs
            verify_mime_type (bool): Whether to verify image MIME types
        """
        super().__init__(channel_id, tenant_id)
        self.max_size_kb = max_size_kb
        self.allow_remote_urls = allow_remote_urls
        self.verify_mime_type = verify_mime_type
    
    def normalize(self, channel_message: Dict[str, Any]) -> Message:
        """
        Convert a channel-specific image message to the standardized internal format.
        
        Args:
            channel_message (Dict[str, Any]): Image message in channel-specific format
            
        Returns:
            Message: Image message in standardized internal format
            
        Raises:
            NormalizationError: If the message cannot be normalized
            ValidationError: If the message validation fails
        """
        self._log_normalization_attempt('normalize')
        
        try:
            # Validate the input message
            self.validate(channel_message)
            
            # Extract basic message properties
            sender_id = self._extract_sender_id(channel_message)
            message_id = self._extract_message_id(channel_message)
            timestamp = self._extract_timestamp(channel_message)
            
            # Extract image-specific data
            image_data = self._extract_image_data(channel_message)
            
            # Process image metadata
            metadata = self.process_metadata(channel_message, image_data)
            
            # Handle caption if present
            caption = self._extract_caption(channel_message)
            
            # Create and return the normalized message
            return Message(
                message_id=message_id,
                channel_id=self.channel_id,
                tenant_id=self.tenant_id,
                sender_id=sender_id,
                message_type=MessageType.IMAGE,
                content=image_data.get("url") or image_data.get("file_id"),
                text=caption,
                entities={},  # We don't currently extract entities from image captions
                metadata=metadata,
                timestamp=timestamp
            )
        
        except (KeyError, ValueError) as e:
            error_msg = f"Failed to normalize image message: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise NormalizationError(error_msg) from e
    
    def denormalize(self, message: Message) -> Dict[str, Any]:
        """
        Convert a standardized internal message to the channel-specific image format.
        
        Args:
            message (Message): Message in standardized internal format
            
        Returns:
            Dict[str, Any]: Image message in channel-specific format
            
        Raises:
            NormalizationError: If the message cannot be denormalized
            ValidationError: If the message validation fails
        """
        self._log_normalization_attempt('denormalize', message.message_id)
        
        try:
            # Validate the message is an image message
            if message.message_type != MessageType.IMAGE:
                raise ValidationError(
                    f"Cannot denormalize non-image message with type {message.message_type}"
                )
            
            # Basic channel-specific message structure
            # This is a generic implementation that should be overridden by channel-specific normalizers
            channel_message = {
                "id": message.message_id,
                "sender": message.sender_id,
                "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                "channel": self.channel_id,
                "tenant": self.tenant_id,
                "type": "image"
            }
            
            # Add image content (URL or file ID)
            if message.content:
                if self._is_url(message.content):
                    channel_message["image_url"] = message.content
                else:
                    channel_message["file_id"] = message.content
            
            # Add caption if present
            if message.text:
                channel_message["caption"] = message.text
            
            # Add metadata
            if message.metadata:
                # Extract relevant image metadata
                if "mime_type" in message.metadata:
                    channel_message["mime_type"] = message.metadata["mime_type"]
                
                if "width" in message.metadata and "height" in message.metadata:
                    channel_message["dimensions"] = {
                        "width": message.metadata["width"],
                        "height": message.metadata["height"]
                    }
                
                if "size" in message.metadata:
                    channel_message["size"] = message.metadata["size"]
                
                # Add any additional metadata as a nested object
                channel_message["metadata"] = message.metadata
            
            return channel_message
        
        except Exception as e:
            error_msg = f"Failed to denormalize image message {message.message_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise NormalizationError(error_msg) from e
    
    def process_metadata(self, channel_message: Dict[str, Any], 
                         image_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process image metadata to extract useful information.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            image_data (Dict[str, Any]): Extracted image data
            
        Returns:
            Dict[str, Any]: Processed metadata
        """
        metadata = self.extract_metadata(channel_message)
        
        # Add image-specific metadata
        if "mime_type" in image_data:
            metadata["mime_type"] = image_data["mime_type"]
        elif "url" in image_data:
            # Try to determine MIME type from URL
            mime_type = self._get_mime_type_from_url(image_data["url"])
            if mime_type:
                metadata["mime_type"] = mime_type
        
        # Add image dimensions if available
        if "width" in image_data and "height" in image_data:
            metadata["width"] = image_data["width"]
            metadata["height"] = image_data["height"]
        
        # Add file size if available
        if "size" in image_data:
            metadata["size"] = image_data["size"]
            
            # Check if image exceeds maximum size
            if self.max_size_kb > 0 and image_data["size"] > self.max_size_kb * 1024:
                logger.warning(
                    f"Image size {image_data['size'] / 1024:.2f}KB exceeds maximum of "
                    f"{self.max_size_kb}KB"
                )
                metadata["exceeds_max_size"] = True
        
        return metadata
    
    def handle_url(self, url: str) -> Dict[str, Any]:
        """
        Process image URLs or references to extract information.
        
        Args:
            url (str): The image URL or reference
            
        Returns:
            Dict[str, Any]: Processed URL data including validity and metadata
            
        Raises:
            ValidationError: If the URL is invalid or not allowed
        """
        result = {"url": url, "is_valid": False}
        
        # Check if it's a URL
        if not self._is_url(url):
            # Might be a file ID or reference, pass it through
            result["is_url"] = False
            result["is_valid"] = True
            return result
        
        # It's a URL, validate it
        result["is_url"] = True
        
        # Check if remote URLs are allowed
        if not self.allow_remote_urls:
            parsed_url = urlparse(url)
            is_remote = parsed_url.scheme in ('http', 'https')
            
            if is_remote:
                raise ValidationError("Remote image URLs are not allowed")
        
        # Validate URL format (basic check)
        if not re.match(r'^(http|https|file)://', url):
            raise ValidationError(f"Invalid URL scheme: {url}")
        
        # Check file extension if verifying MIME types
        if self.verify_mime_type:
            mime_type = self._get_mime_type_from_url(url)
            
            if mime_type:
                result["mime_type"] = mime_type
                
                if mime_type not in SUPPORTED_IMAGE_TYPES:
                    raise ValidationError(f"Unsupported image MIME type: {mime_type}")
            else:
                # No MIME type determined, check extension
                _, ext = os.path.splitext(urlparse(url).path)
                ext = ext.lower()
                
                if ext and ext not in SUPPORTED_IMAGE_EXTENSIONS:
                    raise ValidationError(f"Unsupported image extension: {ext}")
        
        result["is_valid"] = True
        return result
    
    def validate(self, channel_message: Dict[str, Any]) -> bool:
        """
        Validate the structure of a channel-specific image message.
        
        Args:
            channel_message (Dict[str, Any]): The message to validate
            
        Returns:
            bool: True if the message is valid, False otherwise
            
        Raises:
            ValidationError: If the message validation fails with specific details
        """
        super().validate(channel_message)
        
        # Ensure the message is a dictionary
        if not isinstance(channel_message, dict):
            raise ValidationError(f"Expected dict, got {type(channel_message).__name__}")
        
        # Check for required fields
        required_fields = self._get_required_fields()
        missing_fields = [field for field in required_fields if field not in channel_message]
        
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Ensure the message has image data
        try:
            image_data = self._extract_image_data(channel_message)
            
            # Must have either URL, file ID, or binary data
            if not any(k in image_data for k in ["url", "file_id", "data"]):
                raise ValidationError("Image message must contain a URL, file ID, or binary data")
            
            # If URL is present, validate it
            if "url" in image_data:
                self.handle_url(image_data["url"])
                
        except KeyError as e:
            raise ValidationError(f"Invalid image data: {str(e)}")
        
        # If we've made it this far, the message is valid
        return True
    
    def extract_metadata(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from a channel-specific image message.
        
        Args:
            message (Dict[str, Any]): The message to extract metadata from
            
        Returns:
            Dict[str, Any]: Extracted metadata
        """
        metadata = {}
        
        # Extract common metadata fields
        for field in ["timestamp", "message_type", "channel_id", "source"]:
            if field in message:
                metadata[field] = message[field]
        
        # Extract channel-specific metadata (channel implementations should extend this)
        if "metadata" in message and isinstance(message["metadata"], dict):
            metadata.update(message["metadata"])
        
        return metadata
    
    def _extract_image_data(self, channel_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract image-specific data from a channel-specific message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            Dict[str, Any]: Extracted image data
            
        Raises:
            KeyError: If the image data cannot be extracted
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        image_data = {}
        
        # Try to extract image URL
        for field in ["image_url", "url", "media_url", "attachment"]:
            if field in channel_message:
                url_value = channel_message[field]
                # If the field is a dict, it might contain the URL
                if isinstance(url_value, dict) and "url" in url_value:
                    image_data["url"] = url_value["url"]
                elif isinstance(url_value, str):
                    image_data["url"] = url_value
                break
        
        # Try to extract file ID for platforms that use IDs instead of URLs
        for field in ["file_id", "media_id", "attachment_id"]:
            if field in channel_message:
                image_data["file_id"] = channel_message[field]
                break
        
        # Try to extract image dimensions
        if "dimensions" in channel_message:
            dims = channel_message["dimensions"]
            if isinstance(dims, dict):
                if "width" in dims:
                    image_data["width"] = dims["width"]
                if "height" in dims:
                    image_data["height"] = dims["height"]
        else:
            # Try individual dimension fields
            for w_field in ["width", "image_width", "w"]:
                if w_field in channel_message:
                    image_data["width"] = channel_message[w_field]
                    break
            
            for h_field in ["height", "image_height", "h"]:
                if h_field in channel_message:
                    image_data["height"] = channel_message[h_field]
                    break
        
        # Try to extract MIME type
        for field in ["mime_type", "content_type", "media_type"]:
            if field in channel_message:
                image_data["mime_type"] = channel_message[field]
                break
        
        # Try to extract file size
        for field in ["size", "file_size", "media_size"]:
            if field in channel_message:
                image_data["size"] = channel_message[field]
                break
        
        # If we didn't find any image data, raise an error
        if not image_data:
            raise KeyError("Could not extract image data from message")
        
        return image_data
    
    def _extract_caption(self, channel_message: Dict[str, Any]) -> Optional[str]:
        """
        Extract image caption from a channel-specific message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            Optional[str]: The caption, or None if not found
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        for field in ["caption", "text", "description", "alt_text"]:
            if field in channel_message:
                return str(channel_message[field])
        
        return None
    
    def _extract_sender_id(self, channel_message: Dict[str, Any]) -> str:
        """
        Extract the sender ID from a channel-specific message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            str: The sender ID
            
        Raises:
            KeyError: If the sender ID cannot be extracted
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        for field in ["sender_id", "sender", "from", "user_id", "from_user"]:
            if field in channel_message:
                return str(channel_message[field])
        
        raise KeyError("Could not find sender ID in channel message")
    
    def _extract_message_id(self, channel_message: Dict[str, Any]) -> str:
        """
        Extract the message ID from a channel-specific message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            str: The message ID
            
        Raises:
            KeyError: If the message ID cannot be extracted
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        for field in ["id", "message_id", "msg_id"]:
            if field in channel_message:
                return str(channel_message[field])
        
        raise KeyError("Could not find message ID in channel message")
    
    def _extract_timestamp(self, channel_message: Dict[str, Any]) -> Optional[str]:
        """
        Extract the timestamp from a channel-specific message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            Optional[str]: The timestamp, or None if not found
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        for field in ["timestamp", "time", "date", "created_at"]:
            if field in channel_message:
                return channel_message[field]
        
        return None
    
    def _get_required_fields(self) -> Set[str]:
        """
        Get the set of required fields for a valid channel-specific image message.
        
        Returns:
            Set[str]: Set of required field names
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        # At minimum, we need some way to identify the message and the image
        return {"id"}
    
    def _get_message_type(self, channel_message: Dict[str, Any]) -> str:
        """
        Determine if a channel-specific message is an image message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            str: Message type, "image" if it's an image message
        """
        # Check for common fields that indicate an image message
        # This is a generic implementation that should be overridden by channel-specific normalizers
        if "type" in channel_message and channel_message["type"] in ["image", "photo"]:
            return "image"
        
        # Check for presence of image-related fields
        image_fields = ["image_url", "url", "media_url", "attachment", "file_id", "media_id"]
        if any(field in channel_message for field in image_fields):
            return "image"
        
        return "unknown"
    
    def _is_url(self, text: str) -> bool:
        """
        Check if a string is a URL.
        
        Args:
            text (str): The string to check
            
        Returns:
            bool: True if the string is a URL, False otherwise
        """
        if not text:
            return False
        
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _get_mime_type_from_url(self, url: str) -> Optional[str]:
        """
        Determine the MIME type of an image from its URL.
        
        Args:
            url (str): The image URL
            
        Returns:
            Optional[str]: The determined MIME type, or None if cannot be determined
        """
        if not url:
            return None
        
        try:
            # Parse the URL
            parsed_url = urlparse(url)
            
            # Get the path
            path = parsed_url.path
            
            # Get the file extension
            _, ext = os.path.splitext(path)
            
            if not ext:
                return None
            
            # Normalize the extension
            ext = ext.lower()
            
            # Get the MIME type for the extension
            mime_type, _ = mimetypes.guess_type(f"file{ext}")
            
            return mime_type
        except:
            return None