import json
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional, Pattern, Union

import redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.exceptions import CacheError
from app.core.logging import get_logger
from app.adapters.interfaces.cache import CacheStrategy

logger = get_logger(__name__)

class RedisCache(CacheStrategy):
    """Redis-based implementation of the CacheStrategy interface."""
    
    def __init__(
        self,
        host: str = settings.REDIS_HOST,
        port: int = settings.REDIS_PORT,
        password: Optional[str] = settings.REDIS_PASSWORD,
        db: int = settings.REDIS_DB,
        prefix: str = settings.REDIS_PREFIX,
        default_ttl: int = settings.REDIS_DEFAULT_TTL,
        serializer = json,
        **kwargs
    ):
        """
        Initialize the Redis cache.
        
        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            db: Redis database number
            prefix: Key prefix for namespacing
            default_ttl: Default TTL in seconds
            serializer: Object for serializing/deserializing values
            **kwargs: Additional Redis connection options
        """
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.serializer = serializer
        
        # Create Redis client
        try:
            connection_kwargs = {
                "host": host,
                "port": port,
                "db": db,
                **kwargs
            }
            
            # Add password if provided
            if password:
                connection_kwargs["password"] = password
                
            self.client = redis.Redis(**connection_kwargs)
            
            # Test connection
            self.client.ping()
            logger.info("Successfully connected to Redis")
            
        except RedisError as e:
            logger.error(f"Redis connection error: {str(e)}")
            raise CacheError(f"Failed to connect to Redis: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {str(e)}")
            raise CacheError(f"Unexpected error connecting to Redis: {str(e)}")
    
    def _build_key(self, key: str, tenant_id: Optional[str] = None) -> str:
        """
        Build a prefixed cache key with optional tenant namespace.
        
        Args:
            key: Original key
            tenant_id: Optional tenant ID for multi-tenant keys
            
        Returns:
            Prefixed key
        """
        if tenant_id:
            return f"{self.prefix}:{tenant_id}:{key}"
        return f"{self.prefix}:{key}"
    
    async def get(self, key: str, tenant_id: Optional[str] = None) -> Any:
        """
        Get item from cache.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID
            
        Returns:
            Cached value or None if not found
            
        Raises:
            CacheError: If there is a Redis error
        """
        prefixed_key = self._build_key(key, tenant_id)
        
        try:
            # Get value from Redis
            value = self.client.get(prefixed_key)
            
            # Return None if key not found
            if value is None:
                logger.debug(f"Cache miss for key: {prefixed_key}")
                return None
                
            # Deserialize value
            result = self.serializer.loads(value)
            logger.debug(f"Cache hit for key: {prefixed_key}")
            return result
            
        except RedisError as e:
            logger.error(f"Redis error getting key {prefixed_key}: {str(e)}")
            raise CacheError(f"Redis error getting key {key}: {str(e)}")
        except Exception as e:
            logger.error(f"Error deserializing cached value for key {prefixed_key}: {str(e)}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Set item in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds
            tenant_id: Optional tenant ID
            
        Returns:
            True if successful
            
        Raises:
            CacheError: If there is a Redis error
        """
        prefixed_key = self._build_key(key, tenant_id)
        effective_ttl = ttl if ttl is not None else self.default_ttl
        
        try:
            # Serialize value
            serialized = self.serializer.dumps(value)
            
            # Set value in Redis with TTL
            result = self.client.setex(
                prefixed_key,
                effective_ttl,
                serialized
            )
            
            logger.debug(f"Set cache key {prefixed_key} with TTL {effective_ttl}s")
            return result
            
        except RedisError as e:
            logger.error(f"Redis error setting key {prefixed_key}: {str(e)}")
            raise CacheError(f"Redis error setting key {key}: {str(e)}")
        except Exception as e:
            logger.error(f"Error serializing value for key {prefixed_key}: {str(e)}")
            raise CacheError(f"Error serializing value for key {key}: {str(e)}")
    
    async def delete(self, key: str, tenant_id: Optional[str] = None) -> bool:
        """
        Remove item from cache.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID
            
        Returns:
            True if key was found and deleted
            
        Raises:
            CacheError: If there is a Redis error
        """
        prefixed_key = self._build_key(key, tenant_id)
        
        try:
            # Delete key from Redis
            result = self.client.delete(prefixed_key)
            
            # Return True if key was deleted
            deleted = result > 0
            logger.debug(f"Deleted cache key {prefixed_key}: {deleted}")
            return deleted
            
        except RedisError as e:
            logger.error(f"Redis error deleting key {prefixed_key}: {str(e)}")
            raise CacheError(f"Redis error deleting key {key}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error deleting key {prefixed_key}: {str(e)}")
            raise CacheError(f"Unexpected error deleting key {key}: {str(e)}")
    
    async def exists(self, key: str, tenant_id: Optional[str] = None) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID
            
        Returns:
            True if key exists
            
        Raises:
            CacheError: If there is a Redis error
        """
        prefixed_key = self._build_key(key, tenant_id)
        
        try:
            # Check if key exists in Redis
            result = self.client.exists(prefixed_key)
            
            # Return True if key exists
            exists = result > 0
            logger.debug(f"Cache key {prefixed_key} exists: {exists}")
            return exists
            
        except RedisError as e:
            logger.error(f"Redis error checking key {prefixed_key}: {str(e)}")
            raise CacheError(f"Redis error checking key {key}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error checking key {prefixed_key}: {str(e)}")
            raise CacheError(f"Unexpected error checking key {key}: {str(e)}")
    
    async def flush(self, tenant_id: Optional[str] = None) -> int:
        """
        Clear all cache for tenant.
        
        Args:
            tenant_id: Optional tenant ID
            
        Returns:
            Number of keys cleared
            
        Raises:
            CacheError: If there is a Redis error
        """
        try:
            # Build pattern for keys to clear
            if tenant_id:
                pattern = f"{self.prefix}:{tenant_id}:*"
            else:
                pattern = f"{self.prefix}:*"
                
            # Find keys matching pattern
            keys = self.client.keys(pattern)
            
            # If no keys found, return 0
            if not keys:
                logger.debug(f"No keys found for pattern {pattern}")
                return 0
                
            # Delete all matching keys
            result = self.client.delete(*keys)
            
            logger.info(f"Flushed {result} keys for pattern {pattern}")
            return result
            
        except RedisError as e:
            logger.error(f"Redis error flushing keys: {str(e)}")
            raise CacheError(f"Redis error flushing keys: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error flushing keys: {str(e)}")
            raise CacheError(f"Unexpected error flushing keys: {str(e)}")
    
    async def get_keys(self, pattern: str, tenant_id: Optional[str] = None) -> List[str]:
        """
        Get keys matching pattern.
        
        Args:
            pattern: Key pattern
            tenant_id: Optional tenant ID
            
        Returns:
            List of matching keys
            
        Raises:
            CacheError: If there is a Redis error
        """
        try:
            # Build pattern with prefix and optional tenant
            if tenant_id:
                full_pattern = f"{self.prefix}:{tenant_id}:{pattern}"
            else:
                full_pattern = f"{self.prefix}:{pattern}"
                
            # Find keys matching pattern
            keys = self.client.keys(full_pattern)
            
            # Convert bytes to strings and remove prefix
            prefix_len = len(f"{self.prefix}:") + (len(f"{tenant_id}:") if tenant_id else 0)
            result = [k.decode("utf-8")[prefix_len:] for k in keys]
            
            logger.debug(f"Found {len(result)} keys matching pattern {full_pattern}")
            return result
            
        except RedisError as e:
            logger.error(f"Redis error getting keys: {str(e)}")
            raise CacheError(f"Redis error getting keys: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting keys: {str(e)}")
            raise CacheError(f"Unexpected error getting keys: {str(e)}")