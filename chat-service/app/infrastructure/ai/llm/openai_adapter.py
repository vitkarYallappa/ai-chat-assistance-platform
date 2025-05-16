import openai
import tiktoken
from typing import Dict, List, Optional, Any, Generator
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.infrastructure.ai.llm.base_llm import BaseLLM
from app.utils.exceptions import ModelNotAvailableError, TokenLimitExceededError, ModelAPIError

class OpenAIAdapter(BaseLLM):
    """
    OpenAI implementation of the LLM interface.
    Supports text generation using OpenAI models.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the OpenAI adapter with configuration.
        
        Args:
            config: Dictionary containing model configuration
        """
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.organization = config.get("organization")
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = openai.OpenAI(
            api_key=self.api_key,
            organization=self.organization
        )
        
        self.logger.info(f"Initialized OpenAI adapter with model: {self.model_name}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError, openai.RateLimitError))
    )
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate text using OpenAI models.
        
        Args:
            prompt: Input text to generate from
            **kwargs: Additional generation parameters
            
        Returns:
            Dictionary containing generated text and metadata
        """
        try:
            # Merge kwargs with default config, allowing overrides
            params = {
                "model": kwargs.get("model", self.model_name),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", 1.0),
                "n": kwargs.get("n", 1),
                "stop": kwargs.get("stop", None),
                "presence_penalty": kwargs.get("presence_penalty", 0.0),
                "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            }
            
            # Check token count if limit is specified
            if "max_total_tokens" in kwargs:
                token_count = self.count_tokens(prompt)
                if token_count + params["max_tokens"] > kwargs["max_total_tokens"]:
                    raise TokenLimitExceededError(
                        f"Token limit exceeded. Prompt tokens: {token_count}, "
                        f"Max generation tokens: {params['max_tokens']}, "
                        f"Total limit: {kwargs['max_total_tokens']}"
                    )
            
            # Create messages format for chat completion
            messages = [{"role": "user", "content": prompt}]
            if "system_prompt" in kwargs:
                messages.insert(0, {"role": "system", "content": kwargs["system_prompt"]})
            
            # Call OpenAI API
            self.logger.debug(f"Calling OpenAI API with model: {params['model']}")
            response = self.client.chat.completions.create(
                messages=messages,
                **params
            )
            
            # Process response
            result = {
                "text": response.choices[0].message.content,
                "finish_reason": response.choices[0].finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "model": response.model
            }
            
            self.logger.debug(f"Generated {result['usage']['completion_tokens']} tokens")
            return result
            
        except openai.BadRequestError as e:
            error_message = f"Bad request to OpenAI API: {str(e)}"
            self.logger.error(error_message)
            raise ModelAPIError(error_message) from e
            
        except openai.AuthenticationError as e:
            error_message = "Authentication error with OpenAI API. Check API key."
            self.logger.error(error_message)
            raise ModelNotAvailableError(error_message) from e
            
        except (openai.APIError, openai.APIConnectionError) as e:
            error_message = f"OpenAI API error: {str(e)}"
            self.logger.error(error_message)
            # These errors are retried by the decorator
            raise
            
        except openai.RateLimitError as e:
            error_message = "Rate limit exceeded for OpenAI API"
            self.logger.error(error_message)
            # Rate limit errors are retried by the decorator
            raise
            
        except Exception as e:
            error_message = f"Unexpected error in OpenAI adapter: {str(e)}"
            self.logger.exception(error_message)
            raise ModelAPIError(error_message) from e
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError, openai.RateLimitError))
    )
    def stream_generate(self, prompt: str, **kwargs) -> Generator[Dict[str, Any], None, None]:
        """
        Stream generation results token by token from OpenAI.
        
        Args:
            prompt: Input text to generate from
            **kwargs: Additional generation parameters
            
        Returns:
            Generator yielding tokens and metadata
        """
        try:
            # Merge kwargs with default config, allowing overrides
            params = {
                "model": kwargs.get("model", self.model_name),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", 1.0),
                "n": kwargs.get("n", 1),
                "stop": kwargs.get("stop", None),
                "presence_penalty": kwargs.get("presence_penalty", 0.0),
                "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
                "stream": True,
            }
            
            # Create messages format for chat completion
            messages = [{"role": "user", "content": prompt}]
            if "system_prompt" in kwargs:
                messages.insert(0, {"role": "system", "content": kwargs["system_prompt"]})
            
            # Call OpenAI API with streaming
            self.logger.debug(f"Calling OpenAI API with streaming, model: {params['model']}")
            response_stream = self.client.chat.completions.create(
                messages=messages,
                **params
            )
            
            # Stream the response chunks
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield {
                        "token": chunk.choices[0].delta.content,
                        "finish_reason": chunk.choices[0].finish_reason
                    }
            
        except openai.BadRequestError as e:
            error_message = f"Bad request to OpenAI API: {str(e)}"
            self.logger.error(error_message)
            raise ModelAPIError(error_message) from e
            
        except openai.AuthenticationError as e:
            error_message = "Authentication error with OpenAI API. Check API key."
            self.logger.error(error_message)
            raise ModelNotAvailableError(error_message) from e
            
        except (openai.APIError, openai.APIConnectionError) as e:
            error_message = f"OpenAI API error: {str(e)}"
            self.logger.error(error_message)
            # These errors are retried by the decorator
            raise
            
        except openai.RateLimitError as e:
            error_message = "Rate limit exceeded for OpenAI API"
            self.logger.error(error_message)
            # Rate limit errors are retried by the decorator
            raise
            
        except Exception as e:
            error_message = f"Unexpected error in OpenAI adapter: {str(e)}"
            self.logger.exception(error_message)
            raise ModelAPIError(error_message) from e
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken library.
        
        Args:
            text: Input text to count tokens for
            
        Returns:
            Number of tokens in the text
        """
        try:
            # Get the right encoder for the model
            if self.model_name.startswith("gpt-4"):
                encoding = tiktoken.encoding_for_model("gpt-4")
            elif self.model_name.startswith("gpt-3.5-turbo"):
                encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            else:
                # Default to cl100k_base for newer models
                encoding = tiktoken.get_encoding("cl100k_base")
            
            # Count tokens
            token_count = len(encoding.encode(text))
            return token_count
            
        except Exception as e:
            self.logger.error(f"Error counting tokens: {str(e)}")
            # Return an estimate if tiktoken fails
            return len(text) // 4  # Rough approximation
    
    def get_model_details(self) -> Dict[str, Any]:
        """
        Return model specifications for OpenAI.
        
        Returns:
            Dictionary containing model details
        """
        # Model details mapping
        model_details = {
            "gpt-4": {
                "max_context": 8192,
                "training_cutoff": "April 2023",
                "capabilities": ["chat", "reasoning", "code generation"],
                "provider": "OpenAI"
            },
            "gpt-4-turbo": {
                "max_context": 128000,
                "training_cutoff": "April 2023",
                "capabilities": ["chat", "reasoning", "code generation", "extended context"],
                "provider": "OpenAI"
            },
            "gpt-3.5-turbo": {
                "max_context": 4096,
                "training_cutoff": "September 2021",
                "capabilities": ["chat", "basic reasoning", "code generation"],
                "provider": "OpenAI"
            }
        }
        
        # Return details for current model, or generic details if model not in mapping
        return model_details.get(self.model_name, {
            "max_context": self.max_tokens,
            "capabilities": ["text generation"],
            "provider": "OpenAI"
        })
    
    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Process and categorize OpenAI API errors.
        
        Args:
            error: The exception raised by the API call
            
        Returns:
            Dictionary with error details
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        self.logger.error(f"OpenAI API error: {error_type} - {error_message}")
        
        error_categories = {
            "AuthenticationError": "authentication",
            "InvalidRequestError": "invalid_request",
            "RateLimitError": "rate_limit",
            "APIConnectionError": "connection",
            "ServiceUnavailableError": "service_unavailable",
            "APIError": "api_error"
        }
        
        category = error_categories.get(error_type, "unknown")
        
        return {
            "error_type": error_type,
            "error_message": error_message,
            "error_category": category,
            "recoverable": category in ["connection", "rate_limit", "service_unavailable"]
        }