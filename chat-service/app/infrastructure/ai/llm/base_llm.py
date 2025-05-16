from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Generator
import logging

class BaseLLM(ABC):
    """
    Abstract base class for Large Language Model implementations.
    Defines the interface for all LLM adapters.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LLM with configuration.
        
        Args:
            config: Dictionary containing model configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.model_name = config.get("model_name", "default")
        self.max_tokens = config.get("max_tokens", 2048)
        self.temperature = config.get("temperature", 0.7)
        
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Input text to generate from
            **kwargs: Additional generation parameters
            
        Returns:
            Dictionary containing generated text and metadata
        """
        pass
    
    @abstractmethod
    def stream_generate(self, prompt: str, **kwargs) -> Generator[Dict[str, Any], None, None]:
        """
        Stream generation results token by token.
        
        Args:
            prompt: Input text to generate from
            **kwargs: Additional generation parameters
            
        Returns:
            Generator yielding tokens and metadata
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the input text.
        
        Args:
            text: Input text to count tokens for
            
        Returns:
            Number of tokens in the text
        """
        pass
    
    @abstractmethod
    def get_model_details(self) -> Dict[str, Any]:
        """
        Return model specifications and capabilities.
        
        Returns:
            Dictionary containing model details
        """
        pass