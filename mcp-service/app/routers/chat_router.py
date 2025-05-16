from typing import Any, Dict, Optional
import json
import httpx
import asyncio
from datetime import datetime

from app.routers.router_base import RouterBase
from app.domain.models.message import Message
from app.utils.exceptions import RoutingError
from app.utils.retry import retry_async


class ChatRouter(RouterBase):
    """
    Router responsible for routing messages to the Chat Service.
    Handles the communication between the MCP Service and Chat Service.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the chat router with configuration."""
        super().__init__(config)
        self.chat_service_url = self.config.get("chat_service_url", "http://chat-service:8000")
        self.timeout = self.config.get("timeout", 30)  # 30-second timeout by default
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1.0)  # 1-second delay between retries
    
    async def route(self, message: Message, destination: str = "chat") -> Dict[str, Any]:
        """
        Route a message to the Chat Service.
        
        Args:
            message: The message to route
            destination: The destination to route to (default: "chat")
            
        Returns:
            The response from the Chat Service
            
        Raises:
            RoutingError: If the message cannot be routed
        """
        try:
            # Validate the message before routing
            self.validate_message(message)
            
            # Build the request for the Chat Service
            request_data = self.build_request(message)
            
            # Track the message routing for metrics
            self.track_message(message)
            
            # Route the message to the Chat Service with retries
            response = await self.route_to_chat(request_data)
            
            # Process the response from the Chat Service
            processed_response = self.handle_response(response, message)
            
            return processed_response
            
        except Exception as e:
            return self.handle_errors(e, message)
    
    @retry_async(max_retries=3, delay=1.0, backoff=2.0, retryable_exceptions=(httpx.HTTPError, asyncio.TimeoutError))
    async def route_to_chat(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a request to the Chat Service.
        
        Args:
            request_data: The request data to send
            
        Returns:
            The response from the Chat Service
            
        Raises:
            RoutingError: If the message cannot be routed
        """
        self.logger.info(f"Routing message to Chat Service: {request_data.get('message_id')}")
        
        endpoint = f"{self.chat_service_url}/api/v1/messages"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=request_data,
                    headers={
                        "Content-Type": "application/json",
                        "X-Correlation-ID": request_data.get("metadata", {}).get("correlation_id", ""),
                        "X-Tenant-ID": request_data.get("tenant_id", "")
                    }
                )
                
                # Raise for HTTP errors
                response.raise_for_status()
                
                return response.json()
                
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error routing message to Chat Service: {str(e)}")
            raise RoutingError(f"Failed to route message to Chat Service: {str(e)}")
            
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout routing message to Chat Service")
            raise RoutingError(f"Timeout routing message to Chat Service")
            
        except Exception as e:
            self.logger.error(f"Error routing message to Chat Service: {str(e)}", exc_info=True)
            raise RoutingError(f"Failed to route message to Chat Service: {str(e)}")
    
    def build_request(self, message: Message) -> Dict[str, Any]:
        """
        Build a request for the Chat Service.
        
        Args:
            message: The message to build a request for
            
        Returns:
            The request data
        """
        # Extract necessary information from the message
        request_data = {
            "message_id": message.id,
            "conversation_id": message.conversation_id,
            "tenant_id": message.tenant_id,
            "user_id": message.sender_id,
            "content": message.content,
            "timestamp": message.timestamp.isoformat() if message.timestamp else datetime.now().isoformat(),
            "channel_id": message.channel_id,
            "message_type": message.message_type,
            "metadata": message.metadata or {},
        }
        
        # Add attachments if present
        if message.attachments:
            request_data["attachments"] = message.attachments
        
        # Add a correlation ID for tracing
        if "correlation_id" not in request_data["metadata"]:
            from uuid import uuid4
            request_data["metadata"]["correlation_id"] = str(uuid4())
        
        return request_data
    
    def handle_response(self, response: Dict[str, Any], original_message: Message) -> Dict[str, Any]:
        """
        Process the response from the Chat Service.
        
        Args:
            response: The response from the Chat Service
            original_message: The original message that was routed
            
        Returns:
            The processed response
        """
        self.logger.info(f"Received response from Chat Service for message {original_message.id}")
        
        # Check if the response contains an error
        if not response.get("success", True):
            self.logger.warning(f"Chat Service reported an error: {response.get('error')}")
            
            if self.metrics:
                self.metrics.increment("chat_service_errors")
            
            return response
        
        # Add tracking information to the response
        processed_response = {
            **response,
            "routing": {
                "original_message_id": original_message.id,
                "routed_at": datetime.now().isoformat(),
                "router": "chat_router"
            }
        }
        
        # Record successful routing
        if self.metrics:
            self.metrics.increment("messages_routed_success")
            self.metrics.observe("routing_latency", response.get("latency", 0))
        
        return processed_response
    
    def track_message(self, message: Message) -> None:
        """
        Track message routing for metrics.
        
        Args:
            message: The message being routed
        """
        if self.metrics:
            self.metrics.increment("messages_routed", {
                "channel_id": message.channel_id,
                "tenant_id": message.tenant_id,
                "message_type": message.message_type
            })
            
        self.logger.debug(f"Tracking message routing: {message.id}")