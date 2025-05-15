# MCP Service Domain Layer

This directory contains the domain layer for the Message Control Processor (MCP) Service, which is responsible for abstracting channel-specific implementations and normalizing messages across different messaging platforms.

## Overview

The domain layer consists of:

1. **Domain Models** - Core business entities that represent the fundamental concepts of the system
2. **Domain Interfaces** - Abstract base classes that define contracts for implementations
3. **Domain Schemas** - Pydantic models for validating API requests and responses

## Domain Models

### Message

`Message` is the core domain model representing a normalized message in the system. It contains:

- Message content and metadata
- Sender and recipient information
- Channel and tenant identifiers
- Timestamps and message IDs

The `Message` class provides methods for:
- Converting to/from dictionary representations
- Validating message structure and content
- Creating new messages with unique IDs

### Channel

`Channel` represents a messaging platform integration along with its configuration for a specific tenant. It contains:

- Channel identification and metadata
- Tenant-specific configuration
- Capability information (supported message types, features)
- Enabled/disabled status

The `Channel` class provides methods for:
- Checking if specific message/content types are supported
- Retrieving channel capabilities
- Converting to/from dictionary representations

## Domain Interfaces

### ChannelInterface

`ChannelInterface` defines the contract for all channel implementations. It specifies methods that all channel implementations must provide to ensure consistent behavior across different messaging platforms:

- `send_message()` - Sends a message to the channel
- `receive_message()` - Processes incoming messages from the channel
- `normalize_message()` - Converts channel-specific formats to internal format
- `format_response()` - Converts internal format to channel-specific format
- `get_capabilities()` - Returns the capabilities of the channel
- `verify_webhook_signature()` - Verifies webhook signatures
- `is_enabled()` - Checks if the channel is enabled for a tenant

### NormalizerInterface

`NormalizerInterface` defines the contract for message normalizers. It includes methods for:

- `normalize()` - Converts channel-specific formats to internal format
- `denormalize()` - Converts internal format to channel-specific format
- `supports_type()` - Checks if the normalizer supports specific message types
- `extract_metadata()` - Extracts metadata from messages
- `validate()` - Validates normalized messages

## Domain Schemas

### Message Schemas

The message schemas provide Pydantic models for validating message-related API requests and responses:

- `MessageBase` - Base schema for all message-related schemas
- `MessageContent` - Schema for message content
- `MessageCreate` - Schema for creating new messages
- `MessageResponse` - Schema for message responses
- `MessageDeliveryStatus` - Schema for message delivery status updates
- `MessageQuery` - Schema for querying messages

### Enumerations

- `MessageType` - Enumeration of supported message types (text, image, audio, etc.)
- `ContentType` - Enumeration of supported content types (text/plain, image/jpeg, etc.)

## Usage Guidelines

- When implementing a new channel, create a class that implements the `ChannelInterface`
- Use the domain models and schemas for all message processing
- Implement message normalization according to the `NormalizerInterface`
- Follow the message processing pipeline defined in the architecture document

## Example Implementation

```python
from app.domain.interfaces import ChannelInterface
from app.domain.models.message import Message

class WhatsAppChannel(ChannelInterface):
    """WhatsApp channel implementation."""
    
    async def send_message(self, message: Message, tenant_id: str) -> Dict[str, Any]:
        # Implementation for sending a message to WhatsApp
        pass
    
    async def receive_message(self, payload: Dict[str, Any], tenant_id: str) -> Message:
        # Implementation for receiving a message from WhatsApp
        pass
    
    # ... other method implementations
```