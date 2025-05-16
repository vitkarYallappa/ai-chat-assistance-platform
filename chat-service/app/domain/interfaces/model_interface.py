from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from ..models.message import Message
from ..models.intent import Intent

class ModelInterface(ABC):
    """
    Abstract base class defining the interface for AI model implementations.
    Following the Strategy pattern to allow different model implementations.
    """
    
    @abstractmethod
    def generate_response(
        self, 
        messages: List[Message],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Generates a response using the model based on the conversation messages.
        
        Args:
            messages: List of previous messages in the conversation
            max_tokens: Optional maximum number of tokens to generate
            temperature: Optional temperature parameter for generation randomness
            options: Optional additional model-specific parameters
            
        Returns:
            A new Message object containing the generated response
            
        Raises:
            ModelException: If response generation fails
        """
        pass
    
    @abstractmethod
    def classify_intent(self, message: Message) -> Intent:
        """
        Classifies the intent of a user message.
        
        Args:
            message: The user message to classify
            
        Returns:
            An Intent object containing the classification results
            
        Raises:
            ModelException: If intent classification fails
        """
        pass
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        Creates vector embeddings for the provided text.
        
        Args:
            text: The text to embed
            
        Returns:
            A list of floats representing the embedding vector
            
        Raises:
            ModelException: If embedding generation fails
        """
        pass
    
    @abstractmethod
    def calculate_tokens(self, text: str) -> int:
        """
        Calculates the number of tokens in the provided text.
        
        Args:
            text: The text to tokenize
            
        Returns:
            The number of tokens in the text
            
        Raises:
            ModelException: If token calculation fails
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Returns information about the model.
        
        Returns:
            A dictionary containing model specifications
            
        Raises:
            ModelException: If model information retrieval fails
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Checks if the model is currently available for use.
        
        Returns:
            True if the model is available, False otherwise
        """
        pass