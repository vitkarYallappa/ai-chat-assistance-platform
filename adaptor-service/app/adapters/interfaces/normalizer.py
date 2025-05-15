from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Type variables for generics
T = TypeVar('T')  # Generic type for raw data
R = TypeVar('R')  # Generic type for normalized data


class DataFormat(str, Enum):
    """Enum defining supported data formats for normalization."""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    BINARY = "binary"
    TEXT = "text"
    CUSTOM = "custom"


class DataNormalizer(Generic[T, R], ABC):
    """
    Abstract base interface for data normalizers.
    
    This interface defines the standard contract for components that normalize
    data from external APIs into standardized internal formats for the application.
    
    Type Parameters:
        T: The type of raw data from the external API
        R: The type of normalized data after processing
    """
    
    @abstractmethod
    async def normalize_product(self, raw_data: T) -> R:
        """
        Normalizes product data from external API format to standardized format.
        
        Args:
            raw_data: Raw product data from external API
            
        Returns:
            R: Normalized product data in standardized format
            
        Raises:
            ValidationException: If the data cannot be properly normalized
        """
        pass
    
    @abstractmethod
    async def normalize_inventory(self, raw_data: T) -> R:
        """
        Normalizes inventory data from external API format to standardized format.
        
        Args:
            raw_data: Raw inventory data from external API
            
        Returns:
            R: Normalized inventory data in standardized format
            
        Raises:
            ValidationException: If the data cannot be properly normalized
        """
        pass
    
    @abstractmethod
    async def validate(self, normalized_data: R, schema_type: str) -> bool:
        """
        Validates normalized data against a schema.
        
        Args:
            normalized_data: The data to validate
            schema_type: The type of schema to validate against
            
        Returns:
            bool: True if validation succeeds, False otherwise
            
        Raises:
            ValidationException: If validation fails with specific errors
        """
        pass
    
    @abstractmethod
    async def extract_metadata(self, raw_data: T) -> Dict[str, Any]:
        """
        Extracts metadata from raw API responses.
        
        Args:
            raw_data: Raw data from external API
            
        Returns:
            Dict[str, Any]: Dictionary containing metadata such as pagination
                          info, timestamps, version info, etc.
        """
        pass
    
    @abstractmethod
    async def normalize(self, raw_data: T, entity_type: str) -> R:
        """
        Generic normalize method that routes to specific normalizers based on entity type.
        
        Args:
            raw_data: Raw data from external API
            entity_type: Type of entity to normalize (e.g., "product", "inventory")
            
        Returns:
            R: Normalized data in standardized format
            
        Raises:
            ValidationException: If the entity_type is unsupported or data cannot be normalized
        """
        # This implementation can be overridden, but provides a default routing mechanism
        entity_type = entity_type.lower()
        if entity_type == "product":
            return await self.normalize_product(raw_data)
        elif entity_type == "inventory":
            return await self.normalize_inventory(raw_data)
        else:
            logger.error(f"Unsupported entity type for normalization: {entity_type}")
            raise ValueError(f"Unsupported entity type: {entity_type}")
    
    @abstractmethod
    async def format_error(self, error_data: Any) -> Dict[str, Any]:
        """
        Formats error responses from external APIs into a standardized format.
        
        Args:
            error_data: Error data from external API
            
        Returns:
            Dict[str, Any]: Standardized error information
        """
        pass
    
    @abstractmethod
    def supports_data_format(self, data_format: DataFormat) -> bool:
        """
        Checks if this normalizer supports a specific data format.
        
        Args:
            data_format: The format to check support for
            
        Returns:
            bool: True if the format is supported, False otherwise
        """
        pass