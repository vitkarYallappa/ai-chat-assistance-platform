from typing import Any, Dict, Optional

from app.formatters.base import BaseFormatter
from app.domain.models.message import Message
from app.utils.exceptions import FormattingError


class TextFormatter(BaseFormatter):
    """
    Formatter for text messages. Handles the transformation of text messages
    to channel-specific formats.
    """
    
    # Channel-specific text formatting limits
    CHANNEL_LIMITS = {
        "whatsapp": 4096,
        "facebook": 2000,
        "telegram": 4096,
        "webchat": 10000,
        "default": 4000  # Default fallback limit
    }
    
    # Channel-specific formatting options
    CHANNEL_FORMATTING = {
        "whatsapp": {
            "supports_bold": True,
            "supports_italic": True,
            "supports_code": False,
            "supports_links": True
        },
        "facebook": {
            "supports_bold": False,
            "supports_italic": False,
            "supports_code": False,
            "supports_links": True
        },
        "telegram": {
            "supports_bold": True,
            "supports_italic": True,
            "supports_code": True,
            "supports_links": True
        },
        "webchat": {
            "supports_bold": True,
            "supports_italic": True,
            "supports_code": True,
            "supports_links": True
        }
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the text formatter with configuration."""
        super().__init__(config)
    
    def get_supported_types(self) -> list[str]:
        """Return the message types supported by this formatter."""
        return ["text"]
    
    def format(self, message: Message, channel_id: str) -> Dict[str, Any]:
        """
        Format a text message for a specific channel.
        
        Args:
            message: The message to format
            channel_id: The ID of the channel
            
        Returns:
            A dictionary containing the formatted message
            
        Raises:
            FormattingError: If the message cannot be formatted for the channel
        """
        self.logger.info(f"Formatting text message for channel {channel_id}")
        
        if not self.validate_formatting_limits(message, channel_id):
            self.logger.warning(f"Message exceeds length limit for channel {channel_id}")
            message.content = self.truncate_text(message.content, channel_id)
        
        # Process and strip unsupported formatting
        formatted_text = self.add_formatting(message.content, channel_id)
        
        # Build the formatted message
        formatted_message = {
            "type": "text",
            "content": formatted_text,
            "metadata": self.process_metadata(message)
        }
        
        self.logger.debug(f"Text message formatted successfully for channel {channel_id}")
        return formatted_message
    
    def truncate_text(self, text: str, channel_id: str) -> str:
        """
        Truncate text to the channel's maximum length.
        
        Args:
            text: The text to truncate
            channel_id: The ID of the channel
            
        Returns:
            The truncated text
        """
        max_length = self.CHANNEL_LIMITS.get(channel_id, self.CHANNEL_LIMITS["default"])
        
        if len(text) <= max_length:
            return text
        
        # Truncate with ellipsis
        truncated = text[:max_length - 3] + "..."
        return truncated
    
    def add_formatting(self, text: str, channel_id: str) -> str:
        """
        Add channel-specific formatting to text.
        
        Args:
            text: The text to format
            channel_id: The ID of the channel
            
        Returns:
            The formatted text
        """
        channel_format = self.CHANNEL_FORMATTING.get(
            channel_id, {"supports_bold": False, "supports_italic": False, "supports_code": False, "supports_links": True}
        )
        
        # Strip unsupported formatting based on channel capabilities
        if not channel_format["supports_bold"]:
            text = self.strip_unsupported(text, "**", "**")
            
        if not channel_format["supports_italic"]:
            text = self.strip_unsupported(text, "_", "_")
            
        if not channel_format["supports_code"]:
            text = self.strip_unsupported(text, "`", "`")
            
        # Process links if supported
        if channel_format["supports_links"]:
            # Keep links intact
            pass
        else:
            # Extract just the URL text from markdown links
            import re
            text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', text)
        
        return text
    
    def strip_unsupported(self, text: str, start_marker: str, end_marker: str) -> str:
        """
        Remove unsupported formatting markers but keep the content.
        
        Args:
            text: The text to process
            start_marker: The starting format marker
            end_marker: The ending format marker
            
        Returns:
            Text with formatting markers removed
        """
        result = text
        marker_length = len(start_marker)
        
        # Handle nested markers properly
        start_idx = 0
        while True:
            start_pos = result.find(start_marker, start_idx)
            if start_pos == -1:
                break
                
            end_pos = result.find(end_marker, start_pos + marker_length)
            if end_pos == -1:
                break
                
            # Remove the markers but keep the content
            result = result[:start_pos] + result[start_pos + marker_length:end_pos] + result[end_pos + marker_length:]
            
            # Continue searching from the current position
            start_idx = start_pos
        
        return result
    
    def validate_formatting_limits(self, message: Message, channel_id: str) -> bool:
        """
        Check if the message exceeds the channel's length limit.
        
        Args:
            message: The message to validate
            channel_id: The ID of the channel
            
        Returns:
            True if the message is within limits, False otherwise
        """
        max_length = self.CHANNEL_LIMITS.get(channel_id, self.CHANNEL_LIMITS["default"])
        return len(message.content) <= max_length