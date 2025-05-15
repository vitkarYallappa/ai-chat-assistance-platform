from fastapi import APIRouter, Depends, Request, HTTPException, status, Header, Body
from typing import Dict, Any, Optional
import logging
import hmac
import hashlib

from app.config import get_settings
from app.api.dependencies import (
    get_message_service,
    get_correlation_id,
    get_channel_factory
)
from app.domain.exceptions import ChannelException, ValidationException

router = APIRouter()

@router.post(
    "/{channel_id}",
    summary="Handle channel webhook",
    description="Processes incoming webhooks from messaging channels",
    status_code=status.HTTP_200_OK
)
async def handle_webhook(
    channel_id: str,
    request: Request,
    payload: Dict[str, Any] = Body(...),
    x_hub_signature: Optional[str] = Header(None),
    message_service = Depends(get_message_service),
    channel_factory = Depends(get_channel_factory),
    settings = Depends(get_settings),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Generic webhook handler for receiving messages from channels.
    
    Each channel has its own webhook endpoint with channel-specific payload validation.
    The signature is verified if provided in the headers.
    """
    logging.info(
        f"Received webhook for channel {channel_id}",
        extra={
            "correlation_id": correlation_id,
            "channel_id": channel_id
        }
    )
    
    # Get the channel handler
    try:
        channel = channel_factory.get_channel(channel_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel {channel_id} not found"
        )
    
    # Verify webhook signature if required
    if channel.requires_signature_verification():
        webhook_secret = channel.get_webhook_secret()
        
        if not x_hub_signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook signature required"
            )
        
        if not verify_signature(request, x_hub_signature, webhook_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    
    try:
        # Get appropriate webhook handler for the channel
        webhook_handler = channel.get_webhook_handler()
        
        # Process the webhook payload
        result = await webhook_handler.process(payload)
        
        # If the webhook contains messages, process them
        if "messages" in result:
            for message in result["messages"]:
                await message_service.handle_incoming_message(
                    channel_id=channel_id,
                    message=message,
                    metadata=result.get("metadata", {})
                )
        
        # Return channel-specific response
        return webhook_handler.get_response()
    
    except ValidationException as e:
        logging.warning(
            f"Webhook validation error for channel {channel_id}",
            extra={
                "correlation_id": correlation_id,
                "channel_id": channel_id,
                "details": e.details
            }
        )
        
        # Many webhook providers expect a 200 response even for validation errors
        # to prevent re-delivery attempts
        return {"status": "error", "message": "Validation error"}
    
    except ChannelException as e:
        logging.error(
            f"Channel error processing webhook for {channel_id}",
            extra={
                "correlation_id": correlation_id,
                "channel_id": channel_id,
                "details": e.details
            }
        )
        
        # Many webhook providers expect a 200 response even for errors
        # to prevent re-delivery attempts
        return {"status": "error", "message": "Channel processing error"}

def verify_signature(request: Request, provided_signature: str, webhook_secret: str) -> bool:
    """
    Verifies webhook signature using HMAC.
    
    Different channels use different signing algorithms, so this is a simplified example.
    """
    try:
        # For this example, we're using HMAC-SHA1 signing
        raw_body = request.scope["body"]
        
        # Create HMAC signature
        expected_signature = hmac.new(
            webhook_secret.encode(),
            raw_body,
            hashlib.sha1
        ).hexdigest()
        
        # Remove prefix if it exists
        if provided_signature.startswith("sha1="):
            provided_signature = provided_signature[5:]
        
        # Compare signatures using constant-time comparison
        return hmac.compare_digest(expected_signature, provided_signature)
    except Exception as e:
        logging.error(f"Error verifying signature: {str(e)}", exc_info=True)
        return False