"""
Service responsible for intent classification in the Chat Service.

This service handles the classification of user intents from messages,
mapping intents to appropriate handlers, and determining if additional
context is needed. It also matches against FAQs and logs intent data
for analytics.
"""

from typing import Dict, List, Optional, Any
import json
from datetime import datetime

from app.domain.models.message import Message
from app.domain.models.intent import Intent
from app.infrastructure.repositories.intent_repository import IntentRepository
from app.infrastructure.ai.intent.intent_classifier import IntentClassifier
from app.utils.logger import get_logger
from app.utils.exceptions import IntentClassificationError


class IntentService:
    """
    Service responsible for managing intent classification, including
    classifying intents, getting handlers, and matching FAQs.
    """
    
    def __init__(
        self,
        intent_repository: IntentRepository,
        intent_classifier: IntentClassifier
    ):
        """
        Initialize the intent service with dependencies.
        
        Args:
            intent_repository: Repository for intent storage
            intent_classifier: Classifier for intent classification
        """
        self.repository = intent_repository
        self.classifier = intent_classifier
        self.logger = get_logger(__name__)
    
    async def classify_intent(
        self,
        message: Message,
        context: Optional[Dict[str, Any]] = None
    ) -> Intent:
        """
        Classify the intent of a message.
        
        Args:
            message: The message to classify
            context: Optional context for classification
            
        Returns:
            The classified intent
            
        Raises:
            IntentClassificationError: If the intent could not be classified
        """
        try:
            self.logger.info(f"Classifying intent for message: {message.id}")
            
            # Use the classifier to classify the intent
            classification_result = await self.classifier.classify(
                text=message.content,
                context=context
            )
            
            # Get the top intent
            top_intent = classification_result["top_intent"]
            confidence = classification_result["confidence"]
            
            # Create an intent object
            intent = Intent(
                id=top_intent["id"],
                name=top_intent["name"],
                confidence=confidence,
                parameters=top_intent.get("parameters", {}),
                raw_classification=classification_result
            )
            
            # Log the intent
            await self.log_intent(
                message_id=message.id,
                intent=intent,
                tenant_id=message.tenant_id,
                user_id=message.sender_id
            )
            
            self.logger.info(f"Classified intent for message: {message.id} as {intent.name} ({intent.confidence})")
            
            return intent
            
        except Exception as e:
            self.logger.error(f"Failed to classify intent: {str(e)}", exc_info=True)
            
            # Create a fallback intent
            fallback_intent = Intent(
                id="fallback",
                name="fallback",
                confidence=0.0,
                parameters={},
                raw_classification={"error": str(e)}
            )
            
            # Log the fallback
            await self.log_intent(
                message_id=message.id,
                intent=fallback_intent,
                tenant_id=message.tenant_id,
                user_id=message.sender_id,
                is_fallback=True
            )
            
            raise IntentClassificationError(f"Failed to classify intent: {str(e)}")
    
    async def get_intent_handlers(self, intent: Intent) -> List[Dict[str, Any]]:
        """
        Get handlers for an intent.
        
        Args:
            intent: The intent to get handlers for
            
        Returns:
            List of handlers for the intent
        """
        try:
            self.logger.debug(f"Getting handlers for intent: {intent.name}")
            
            # Get the intent configuration
            intent_config = await self.repository.get_by_id(intent.id)
            
            if not intent_config:
                self.logger.warning(f"No configuration found for intent: {intent.id}")
                return []
                
            # Get the handlers
            handlers = intent_config.get("handlers", [])
            
            if not handlers:
                self.logger.warning(f"No handlers found for intent: {intent.id}")
                
            return handlers
            
        except Exception as e:
            self.logger.error(f"Failed to get intent handlers: {str(e)}", exc_info=True)
            return []
    
    def should_retrieve_context(self, intent: Intent) -> bool:
        """
        Determine if additional context is needed for an intent.
        
        Args:
            intent: The intent to check
            
        Returns:
            True if context should be retrieved, False otherwise
        """
        try:
            # Check if the intent requires context
            context_required = intent.raw_classification.get("context_required", False)
            
            # Check if the confidence is below a threshold
            low_confidence = intent.confidence < 0.7
            
            # Check if the intent is a follow-up
            is_followup = intent.raw_classification.get("is_followup", False)
            
            # Determine if context should be retrieved
            should_retrieve = context_required or low_confidence or is_followup
            
            if should_retrieve:
                self.logger.debug(f"Context should be retrieved for intent: {intent.name}")
            
            return should_retrieve
            
        except Exception as e:
            self.logger.warning(f"Error checking if context should be retrieved: {str(e)}")
            # Default to retrieving context in case of error
            return True
    
    async def match_faq(
        self,
        message: Message,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Match a message against frequently asked questions.
        
        Args:
            message: The message to match
            tenant_id: ID of the tenant
            
        Returns:
            Matched FAQ or None if no match
        """
        try:
            self.logger.debug(f"Matching FAQ for message: {message.id}")
            
            # Get FAQs for the tenant
            faqs = await self.repository.get_faqs(tenant_id)
            
            if not faqs:
                self.logger.debug(f"No FAQs found for tenant: {tenant_id}")
                return None
                
            # Use the classifier to match against FAQs
            match_result = await self.classifier.match_faq(
                text=message.content,
                faqs=faqs
            )
            
            if not match_result or match_result["confidence"] < 0.8:
                self.logger.debug(f"No high-confidence FAQ match for message: {message.id}")
                return None
                
            self.logger.info(f"Matched FAQ for message: {message.id} with confidence {match_result['confidence']}")
            
            return match_result
            
        except Exception as e:
            self.logger.error(f"Failed to match FAQ: {str(e)}", exc_info=True)
            return None
    
    async def log_intent(
        self,
        message_id: str,
        intent: Intent,
        tenant_id: str,
        user_id: str,
        is_fallback: bool = False
    ) -> None:
        """
        Log intent classification for analytics.
        
        Args:
            message_id: ID of the message
            intent: The classified intent
            tenant_id: ID of the tenant
            user_id: ID of the user
            is_fallback: Whether this is a fallback intent
        """
        try:
            self.logger.debug(f"Logging intent for message: {message_id}")
            
            # Create intent log entry
            intent_log = {
                "message_id": message_id,
                "intent_id": intent.id,
                "intent_name": intent.name,
                "confidence": intent.confidence,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "parameters": json.dumps(intent.parameters),
                "is_fallback": is_fallback
            }
            
            # Save the log entry
            await self.repository.log_intent(intent_log)
            
            self.logger.debug(f"Logged intent for message: {message_id}")
            
        except Exception as e:
            self.logger.warning(f"Failed to log intent: {str(e)}")
            # Non-critical error, so we don't raise an exception