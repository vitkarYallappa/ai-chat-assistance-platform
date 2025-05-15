from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union, Tuple
from enum import Enum
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# Type variables for generics
K = TypeVar('K')  # Generic type for cache keys
V = TypeVar('V')  # Generic type for cache values


class CacheLevel(str, Enum):
    """Enum defining cache storage levels."""
    MEMORY = "memory"
    REDIS = "redis"
    DISTRIBUTED = "distributed"
    MULTI_LEVEL = "multi_level"


class CacheTTLStrategy(str, Enum):
    """Enum defining TTL (Time To Live) strategies for cached items."""
    FIXED = "fixed"
    SLIDING = "sliding"
    ADAPTIVE = "adaptive"  # Adjusts based on access patterns
    INFINITE = "infinite"  # No expiration


class CacheStrategy(Generic[K, V], ABC):
    """
    Abstract base interface for caching strategies.
    
    This interface defines the standard contract for components that handle
    caching of data to improve performance and reduce load on external APIs.
    
    Type Parameters:
        K: The type of keys used for cache entries
        V: The type of values stored in the cache
    """
    
    @abstractmethod
    async def get(self, key: K) -> Optional[V]:
        """
        Retrieves a cached item by key.
        
        Args:
            key: The key of the item to retrieve
            
        Returns:
            Optional[V]: The cached value if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def set(self, key: K, value: V, ttl: Optional[int] = None) -> bool:
        """
        Stores an item in the cache.
        
        Args:
            key: The key to store the value under
            value: The value to store
            ttl: Optional time-to-live in seconds
            
        Returns:
            bool: True if successfully cached, False otherwise
        """
        pass
    
    @abstractmethod
    async def invalidate(self, key: K) -> bool:
        """
        Removes an item from the cache.
        
        Args:
            key: The key of the item to remove
            
        Returns:
            bool: True if successfully removed or not present, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_many(self, keys: List[K]) -> Dict[K, V]:
        """
        Retrieves multiple cached items by their keys.
        
        Args:
            keys: List of keys to retrieve
            
        Returns:
            Dict[K, V]: Dictionary mapping found keys to their values
                       (missing keys are not included)
        """
        pass
    
    @abstractmethod
    async def set_many(self, items: Dict[K, V], ttl: Optional[int] = None) -> bool:
        """
        Stores multiple items in the cache.
        
        Args:
            items: Dictionary mapping keys to values
            ttl: Optional time-to-live in seconds
            
        Returns:
            bool: True if all items were successfully cached, False otherwise
        """
        pass
    
    @abstractmethod
    async def clear(self, namespace: Optional[str] = None) -> bool:
        """
        Clears the cache or a namespace within the cache.
        
        Args:
            namespace: Optional namespace to clear. If None, clears entire cache.
            
        Returns:
            bool: True if successfully cleared, False otherwise
        """
        pass
    
    @abstractmethod
    async def exists(self, key: K) -> bool:
        """
        Checks if a key exists in the cache.
        
        Args:
            key: The key to check
            
        Returns:
            bool: True if the key exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_or_set(self, key: K, value_func: callable, ttl: Optional[int] = None) -> V:
        """
        Retrieves an item from cache or sets it using the provided function.
        
        Args:
            key: The key to look up or store under
            value_func: Function to call to generate the value if not in cache
            ttl: Optional time-to-live in seconds
            
        Returns:
            V: The value from cache or newly generated
        """
        # Default implementation
        value = await self.get(key)
        if value is None:
            value = await value_func()
            await self.set(key, value, ttl)
        return value
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Returns statistics about the cache.
        
        Returns:
            Dict[str, Any]: Statistics including hit rate, miss rate, etc.
        """
        pass
    
    @abstractmethod
    async def get_with_metadata(self, key: K) -> Tuple[Optional[V], Optional[Dict[str, Any]]]:
        """
        Retrieves a cached item along with its metadata.
        
        Args:
            key: The key of the item to retrieve
            
        Returns:
            Tuple[Optional[V], Optional[Dict[str, Any]]]: The cached value and metadata if found,
                                                       (None, None) otherwise
        """
        pass
    
    @abstractmethod
    def key_to_string(self, key: K) -> str:
        """
        Converts a key to a string representation for storage.
        
        Args:
            key: The key to convert
            
        Returns:
            str: String representation of the key
        """
        # Default implementation
        if isinstance(key, str):
            return key
        return str(key)