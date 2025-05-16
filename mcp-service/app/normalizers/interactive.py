"""
Interactive Message Normalizer Module.

This module implements the normalizer for interactive messages (buttons, lists, menus, etc.)
in the MCP Service. The InteractiveNormalizer converts channel-specific interactive message
formats to/from the standardized internal format.
"""

import json
from typing import Any, Dict, List, Optional, Set, Union

from app.domain.models.message import Message, MessageType, InteractiveElement
from app.normalizers.base import BaseNormalizer
from app.utils.logger import get_logger
from app.utils.exceptions import NormalizationError, ValidationError

logger = get_logger(__name__)

# Interactive element types
INTERACTIVE_TYPES = {
    "button", "list", "menu", "quick_reply", "carousel", "card", "action", "selection"
}


class InteractiveNormalizer(BaseNormalizer):
    """
    Normalizer for interactive messages across different channels.
    
    Converts channel-specific interactive message formats to/from the standardized
    internal message format. Interactive messages include buttons, lists, menus,
    quick replies, carousels, and other interactive elements.
    """
    
    def __init__(self, channel_id: str, tenant_id: str, 
                 max_elements: int = 10,
                 validate_structure: bool = True):
        """
        Initialize the interactive normalizer with configuration.
        
        Args:
            channel_id (str): The identifier for the messaging channel
            tenant_id (str): The identifier for the tenant
            max_elements (int): Maximum allowed interactive elements
            validate_structure (bool): Whether to validate interactive element structure
        """
        super().__init__(channel_id, tenant_id)
        self.max_elements = max_elements
        self.validate_structure = validate_structure
    
    def normalize(self, channel_message: Dict[str, Any]) -> Message:
        """
        Convert a channel-specific interactive message to the standardized internal format.
        
        Args:
            channel_message (Dict[str, Any]): Interactive message in channel-specific format
            
        Returns:
            Message: Interactive message in standardized internal format
            
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
            
            # Extract text content if present
            text_content = self._extract_text_content(channel_message)
            
            # Extract interactive elements
            interactive_elements = self._extract_interactive_elements(channel_message)
            
            # Extract metadata
            metadata = self.extract_metadata(channel_message)
            
            # Add interactive element type to metadata
            if interactive_elements:
                # Set the interactive type in metadata for reference
                metadata["interactive_type"] = self._determine_interactive_type(channel_message)
                metadata["interactive_count"] = len(interactive_elements)
            
            # Create and return the normalized message
            return Message(
                message_id=message_id,
                channel_id=self.channel_id,
                tenant_id=self.tenant_id,
                sender_id=sender_id,
                message_type=MessageType.INTERACTIVE,
                content=json.dumps(interactive_elements) if interactive_elements else "",
                text=text_content,
                entities={},  # We don't currently extract entities from interactive messages
                metadata=metadata,
                timestamp=timestamp
            )
        
        except (KeyError, ValueError) as e:
            error_msg = f"Failed to normalize interactive message: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise NormalizationError(error_msg) from e
    
    def denormalize(self, message: Message) -> Dict[str, Any]:
        """
        Convert a standardized internal message to the channel-specific interactive format.
        
        Args:
            message (Message): Message in standardized internal format
            
        Returns:
            Dict[str, Any]: Interactive message in channel-specific format
            
        Raises:
            NormalizationError: If the message cannot be denormalized
            ValidationError: If the message validation fails
        """
        self._log_normalization_attempt('denormalize', message.message_id)
        
        try:
            # Validate the message is an interactive message
            if message.message_type != MessageType.INTERACTIVE:
                raise ValidationError(
                    f"Cannot denormalize non-interactive message with type {message.message_type}"
                )
            
            # Basic channel-specific message structure
            # This is a generic implementation that should be overridden by channel-specific normalizers
            channel_message = {
                "id": message.message_id,
                "sender": message.sender_id,
                "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                "channel": self.channel_id,
                "tenant": self.tenant_id,
                "type": "interactive"
            }
            
            # Add text content if present
            if message.text:
                channel_message["text"] = message.text
            
            # Parse and add interactive elements
            interactive_elements = []
            if message.content:
                try:
                    interactive_elements = json.loads(message.content)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse interactive elements: {str(e)}")
                    # Continue without interactive elements
            
            # Build interactive elements for the channel
            channel_message["interactive"] = self.build_interactive_elements(
                interactive_elements, message.metadata.get("interactive_type", "button")
            )
            
            # Add metadata
            if message.metadata:
                # Add any additional metadata as a nested object
                channel_message["metadata"] = message.metadata
            
            return channel_message
        
        except Exception as e:
            error_msg = f"Failed to denormalize interactive message {message.message_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise NormalizationError(error_msg) from e
    
    def extract_selection(self, channel_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user selection data from an interactive response message.
        
        Args:
            channel_message (Dict[str, Any]): The interactive response message
            
        Returns:
            Dict[str, Any]: User selection data
            
        Raises:
            ValidationError: If the selection cannot be extracted or is invalid
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        selection = {}
        
        # Check common fields for selection data
        for field in ["selected", "selection", "action", "response", "payload"]:
            if field in channel_message:
                selection_data = channel_message[field]
                
                # If the selection is a string, try to parse it as JSON
                if isinstance(selection_data, str):
                    try:
                        parsed_data = json.loads(selection_data)
                        if isinstance(parsed_data, dict):
                            selection = parsed_data
                        else:
                            selection = {"value": parsed_data}
                    except json.JSONDecodeError:
                        # Not valid JSON, use as raw value
                        selection = {"value": selection_data}
                
                # If the selection is a dict, use it directly
                elif isinstance(selection_data, dict):
                    selection = selection_data
                
                # If the selection is some other type, store it as a value
                else:
                    selection = {"value": selection_data}
                
                break
        
        # If we couldn't find any selection data, raise an error
        if not selection:
            raise ValidationError("Could not extract selection data from interactive message")
        
        # Ensure the selection has at least an ID or value
        if "id" not in selection and "value" not in selection:
            raise ValidationError("Selection data must contain an ID or value")
        
        return selection
    
    def build_interactive_elements(self, elements: List[Dict[str, Any]], 
                                  element_type: str = "button") -> Dict[str, Any]:
        """
        Creates channel-specific interactive elements from standardized elements.
        
        Args:
            elements (List[Dict[str, Any]]): Standardized interactive elements
            element_type (str): Type of interactive element to build
            
        Returns:
            Dict[str, Any]: Channel-specific interactive elements structure
            
        Raises:
            ValueError: If the elements cannot be built
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        if not elements:
            return {}
        
        # Validate element type
        if element_type not in INTERACTIVE_TYPES:
            element_type = "button"  # Default to button if type is unknown
        
        # Default structure for common interactive types
        if element_type == "button":
            return {
                "type": "button",
                "buttons": [
                    {
                        "id": e.get("id", f"btn_{i}"),
                        "title": e.get("text", "Button"),
                        "payload": e.get("payload", e.get("value", "")),
                        "style": e.get("style", "default")
                    }
                    for i, e in enumerate(elements[:self.max_elements])
                ]
            }
        
        elif element_type == "list":
            return {
                "type": "list",
                "title": "Select an option",
                "items": [
                    {
                        "id": e.get("id", f"item_{i}"),
                        "title": e.get("text", "Item"),
                        "description": e.get("description", ""),
                        "payload": e.get("payload", e.get("value", ""))
                    }
                    for i, e in enumerate(elements[:self.max_elements])
                ]
            }
        
        elif element_type == "quick_reply":
            return {
                "type": "quick_reply",
                "replies": [
                    {
                        "id": e.get("id", f"qr_{i}"),
                        "title": e.get("text", "Reply"),
                        "payload": e.get("payload", e.get("value", ""))
                    }
                    for i, e in enumerate(elements[:self.max_elements])
                ]
            }
        
        else:
            # Generic fallback for other types
            return {
                "type": element_type,
                "elements": elements[:self.max_elements]
            }
    
    def validate(self, channel_message: Dict[str, Any]) -> bool:
        """
        Validate the structure of a channel-specific interactive message.
        
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
        
        # Check if this is an interactive message
        if self._determine_interactive_type(channel_message) == "unknown":
            raise ValidationError("Message does not contain interactive elements")
        
        # Check interactive elements if validation is enabled
        if self.validate_structure:
            interactive_elements = self._extract_interactive_elements(channel_message)
            
            if not interactive_elements:
                raise ValidationError("No interactive elements found in message")
            
            if len(interactive_elements) > self.max_elements:
                logger.warning(
                    f"Message contains {len(interactive_elements)} interactive elements, "
                    f"which exceeds the maximum of {self.max_elements}"
                )
            
            # Validate each interactive element
            for i, element in enumerate(interactive_elements):
                if not isinstance(element, dict):
                    raise ValidationError(
                        f"Interactive element {i} is not a dictionary: {element}"
                    )
                
                # Check for required element properties
                if "id" not in element and "text" not in element:
                    raise ValidationError(
                        f"Interactive element {i} missing both 'id' and 'text': {element}"
                    )
        
        # If we've made it this far, the message is valid
        return True
    
    def extract_metadata(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from a channel-specific interactive message.
        
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
        
        # Extract interactive-specific metadata
        interactive_type = self._determine_interactive_type(message)
        if interactive_type != "unknown":
            metadata["interactive_type"] = interactive_type
        
        # Extract channel-specific metadata (channel implementations should extend this)
        if "metadata" in message and isinstance(message["metadata"], dict):
            metadata.update(message["metadata"])
        
        return metadata
    
    def _extract_interactive_elements(self, 
                                      channel_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract interactive elements from a channel-specific message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            List[Dict[str, Any]]: List of interactive elements
            
        Raises:
            KeyError: If the interactive elements cannot be extracted
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        interactive_type = self._determine_interactive_type(channel_message)
        
        if interactive_type == "unknown":
            return []
        
        elements = []
        
        # Extract elements based on the interactive type
        if interactive_type == "button":
            # Look for buttons in common formats
            buttons = None
            
            if "buttons" in channel_message:
                buttons = channel_message["buttons"]
            elif "interactive" in channel_message and "buttons" in channel_message["interactive"]:
                buttons = channel_message["interactive"]["buttons"]
            
            if buttons and isinstance(buttons, list):
                for button in buttons:
                    if isinstance(button, dict):
                        element = {
                            "type": "button",
                            "id": button.get("id", button.get("payload", "")),
                            "text": button.get("title", button.get("text", "Button")),
                            "payload": button.get("payload", button.get("value", "")),
                            "style": button.get("style", "default")
                        }
                        elements.append(element)
        
        elif interactive_type == "list":
            # Look for list items in common formats
            items = None
            
            if "items" in channel_message:
                items = channel_message["items"]
            elif "list" in channel_message:
                items = channel_message["list"].get("items", [])
            elif "interactive" in channel_message and "items" in channel_message["interactive"]:
                items = channel_message["interactive"]["items"]
            
            if items and isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        element = {
                            "type": "list_item",
                            "id": item.get("id", item.get("payload", "")),
                            "text": item.get("title", item.get("text", "Item")),
                            "description": item.get("description", ""),
                            "payload": item.get("payload", item.get("value", ""))
                        }
                        elements.append(element)
        
        elif interactive_type == "quick_reply":
            # Look for quick replies in common formats
            replies = None
            
            if "quick_replies" in channel_message:
                replies = channel_message["quick_replies"]
            elif "replies" in channel_message:
                replies = channel_message["replies"]
            elif "interactive" in channel_message and "replies" in channel_message["interactive"]:
                replies = channel_message["interactive"]["replies"]
            
            if replies and isinstance(replies, list):
                for reply in replies:
                    if isinstance(reply, dict):
                        element = {
                            "type": "quick_reply",
                            "id": reply.get("id", reply.get("payload", "")),
                            "text": reply.get("title", reply.get("text", "Reply")),
                            "payload": reply.get("payload", reply.get("value", ""))
                        }
                        elements.append(element)
        
        else:
            # Generic handling for other types
            # Try to find elements in common locations
            for field in ["elements", "items", "buttons", "replies", "actions"]:
                if field in channel_message:
                    items = channel_message[field]
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                # Try to extract common fields
                                element = {
                                    "type": interactive_type,
                                    "id": item.get("id", ""),
                                    "text": item.get("title", item.get("text", "")),
                                }
                                
                                # Add any additional fields
                                for k, v in item.items():
                                    if k not in ["id", "title", "text"]:
                                        element[k] = v
                                
                                elements.append(element)
                        
                        # If we found elements, no need to check other fields
                        if elements:
                            break
        
        return elements
    
    def _determine_interactive_type(self, channel_message: Dict[str, Any]) -> str:
        """
        Determine the type of interactive message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            str: The determined interactive type, or "unknown" if cannot be determined
        """
        # Check for explicit type field
        if "type" in channel_message:
            msg_type = channel_message["type"].lower()
            if msg_type in INTERACTIVE_TYPES:
                return msg_type
        
        # Check for interactive field
        if "interactive" in channel_message:
            interactive = channel_message["interactive"]
            if isinstance(interactive, dict) and "type" in interactive:
                int_type = interactive["type"].lower()
                if int_type in INTERACTIVE_TYPES:
                    return int_type
        
        # Check for presence of specific interactive elements
        if "buttons" in channel_message:
            return "button"
        elif "quick_replies" in channel_message or "replies" in channel_message:
            return "quick_reply"
        elif "items" in channel_message or "list" in channel_message:
            return "list"
        elif "carousel" in channel_message:
            return "carousel"
        elif "card" in channel_message:
            return "card"
        
        # If we couldn't determine the type, return unknown
        return "unknown"
    
    def _extract_text_content(self, channel_message: Dict[str, Any]) -> Optional[str]:
        """
        Extract text content from a channel-specific interactive message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            Optional[str]: The text content, or None if not found
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        for field in ["text", "content", "header", "title", "message", "body"]:
            if field in channel_message:
                return str(channel_message[field])
        
        # Check in nested interactive object
        if "interactive" in channel_message and isinstance(channel_message["interactive"], dict):
            interactive = channel_message["interactive"]
            for field in ["text", "content", "header", "title"]:
                if field in interactive:
                    return str(interactive[field])
        
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
        Get the set of required fields for a valid channel-specific interactive message.
        
        Returns:
            Set[str]: Set of required field names
        """
        # This is a generic implementation that should be overridden by channel-specific normalizers
        # At minimum, we need some way to identify the message
        return {"id"}
    
    def _get_message_type(self, channel_message: Dict[str, Any]) -> str:
        """
        Determine if a channel-specific message is an interactive message.
        
        Args:
            channel_message (Dict[str, Any]): The channel-specific message
            
        Returns:
            str: Message type, "interactive" if it's an interactive message
        """
        interactive_type = self._determine_interactive_type(channel_message)
        if interactive_type != "unknown":
            return "interactive"
        
        return "unknown"