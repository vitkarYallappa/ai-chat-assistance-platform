from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

class IntentType(Enum):
    """Enumeration of common intent types"""
    GREETING = "greeting"
    PRODUCT_QUERY = "product_query"
    SUPPORT = "support"
    ORDER_STATUS = "order_status"
    CHECKOUT = "checkout"
    GENERAL_QUESTION = "general_question"
    FAREWELL = "farewell"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class IntentClassification:
    """
    Immutable value object representing a specific intent classification with confidence.
    """
    intent_type: IntentType
    confidence: float
    parameters: Optional[Dict[str, Any]] = None

class Intent:
    """
    Domain model representing a classified intent from a user message.
    Follows the Value Object pattern with immutable properties.
    """
    
    def __init__(
        self, 
        primary_classification: IntentClassification,
        secondary_classifications: Optional[List[IntentClassification]] = None,
        requires_context: bool = False,
        message_id: Optional[str] = None
    ):
        """
        Initialize a new intent classification result.
        
        Args:
            primary_classification: The primary intent classification
            secondary_classifications: Optional list of secondary/alternative classifications
            requires_context: Whether this intent requires additional context to process
            message_id: Optional ID of the message this intent was derived from
        """
        self._primary = primary_classification
        self._secondary = secondary_classifications or []
        self._requires_context = requires_context
        self._message_id = message_id
    
    @property
    def primary(self) -> IntentClassification:
        return self._primary
    
    @property
    def secondary(self) -> List[IntentClassification]:
        return self._secondary.copy()  # Return a copy to prevent modification
    
    @property
    def message_id(self) -> Optional[str]:
        return self._message_id
    
    def get_confidence(self) -> float:
        """
        Returns the confidence score of the primary intent classification.
        
        Returns:
            Float between 0-1 representing confidence
        """
        return self._primary.confidence
    
    def is_product_query(self) -> bool:
        """
        Checks if this intent is related to product information.
        
        Returns:
            True if the intent is a product query, False otherwise
        """
        return self._primary.intent_type == IntentType.PRODUCT_QUERY
    
    def requires_context(self) -> bool:
        """
        Determines if this intent requires retrieval of additional context.
        
        Returns:
            True if context retrieval is needed, False otherwise
        """
        return self._requires_context
    
    def get_top_intents(self, threshold: float = 0.2) -> List[IntentClassification]:
        """
        Returns all intent classifications above a confidence threshold.
        
        Args:
            threshold: Minimum confidence threshold (default 0.2)
            
        Returns:
            List of intent classifications above the threshold
        """
        result = [self._primary] if self._primary.confidence >= threshold else []
        result.extend([i for i in self._secondary if i.confidence >= threshold])
        return sorted(result, key=lambda x: x.confidence, reverse=True)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Intent):
            return False
        return (
            self._primary.intent_type == other._primary.intent_type and
            abs(self._primary.confidence - other._primary.confidence) < 0.001
        )
    
    def __repr__(self) -> str:
        return f"Intent(primary={self._primary.intent_type.value}, " \
               f"confidence={self._primary.confidence:.2f}, " \
               f"requires_context={self._requires_context})"