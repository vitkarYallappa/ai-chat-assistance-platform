import json
import logging
import asyncio
from datetime import timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypeVar, Callable
import hashlib
import pickle
import uuid
import time
from functools import wraps


import redis
from redis.exceptions import RedisError
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import CacheError
from app.core.logging import get_logger
from app.adapters.interfaces.cache import CacheStrategy

logger = get_logger(__name__)

# Type variable for generic cache value types
T = TypeVar('T')


class CacheMetadata(BaseModel):
    """Metadata for cached items."""
    key: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    tags: Set[str] = set()
    version: str = "1"
    
    class Config:
        arbitrary_types_allowed = True


class CachedItem(BaseModel):
    """A cached item with its value and metadata."""
    value: Any
    metadata: CacheMetadata
    
    class Config:
        arbitrary_types_allowed = True


class InvalidationRule(BaseModel):
    """Rule for automatic cache invalidation."""
    tag: str
    pattern: Optional[str] = None
    ttl: Optional[int] = None


class RefreshConfig(BaseModel):
    """Configuration for background cache refreshing."""
    enabled: bool = False
    threshold_seconds: int = 60  # Refresh if within this many seconds of expiry
    async_refresh: bool = True
    stale_ttl: Optional[int] = 300  # How long to keep stale data if refresh fails


class CircuitBreakerState(str, Enum):
    """State enum for the circuit breaker pattern."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Preventing calls to Redis
    HALF_OPEN = "half_open"  # Testing if Redis is back


class CircuitBreakerConfig(BaseModel):
    """Configuration for the Redis circuit breaker."""
    enabled: bool = True
    failure_threshold: int = 5  # Number of failures before opening
    reset_timeout: int = 30     # Seconds before trying again
    
    class Config:
        arbitrary_types_allowed = True
        
        

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
        
        
        
class RedisCacheClient:
    """Client for interacting with Redis cache with advanced features."""
    
    def __init__(
        self,
        redis_client: Redis,
        logger: logging.Logger,
        default_ttl: int = 3600,
        serializer: Optional[Callable[[Any], bytes]] = None,
        deserializer: Optional[Callable[[bytes], Any]] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize the Redis cache client.
        
        Args:
            redis_client: Redis client instance
            logger: Logger instance
            default_ttl: Default TTL for cache items in seconds
            serializer: Custom serializer function
            deserializer: Custom deserializer function
            circuit_breaker_config: Circuit breaker configuration
        """
        self.redis = redis_client
        self.logger = logger
        self.default_ttl = default_ttl
        
        # Set serializer/deserializer with defaults
        self.serializer = serializer or self._default_serializer
        self.deserializer = deserializer or self._default_deserializer
        
        # Circuit breaker configuration
        if circuit_breaker_config is None:
            circuit_breaker_config = CircuitBreakerConfig()
        self.circuit_breaker = self._create_circuit_breaker(circuit_breaker_config)
        
        # Keep track of registered invalidation rules
        self.invalidation_rules: List[InvalidationRule] = []
        
        # Initialize background tasks
        self._bg_tasks: Set[asyncio.Task] = set()

    def _create_circuit_breaker(self, config: CircuitBreakerConfig) -> Dict[str, Any]:
        """Create the circuit breaker state dictionary."""
        return {
            "state": CircuitBreakerState.CLOSED,
            "failure_count": 0,
            "last_failure_time": None,
            "config": config,
        }
    
    def _update_circuit_breaker(self, success: bool) -> None:
        """Update circuit breaker state based on operation success/failure."""
        if not self.circuit_breaker["config"].enabled:
            return
            
        if success:
            # Reset on success
            if self.circuit_breaker["state"] in (CircuitBreakerState.HALF_OPEN, CircuitBreakerState.OPEN):
                self.logger.info("Redis circuit breaker reset to CLOSED")
                self.circuit_breaker["state"] = CircuitBreakerState.CLOSED
            self.circuit_breaker["failure_count"] = 0
        else:
            # Handle failure
            if self.circuit_breaker["state"] == CircuitBreakerState.CLOSED:
                self.circuit_breaker["failure_count"] += 1
                
                # Check if we should open the circuit
                if self.circuit_breaker["failure_count"] >= self.circuit_breaker["config"].failure_threshold:
                    self.logger.warning(
                        f"Redis circuit breaker OPENED after {self.circuit_breaker['failure_count']} failures"
                    )
                    self.circuit_breaker["state"] = CircuitBreakerState.OPEN
                    self.circuit_breaker["last_failure_time"] = time.time()
            
            # If the circuit is already open, update the failure time
            elif self.circuit_breaker["state"] == CircuitBreakerState.OPEN:
                self.circuit_breaker["last_failure_time"] = time.time()
                
            # If the circuit is half-open, reopen it on failure
            elif self.circuit_breaker["state"] == CircuitBreakerState.HALF_OPEN:
                self.logger.warning("Redis circuit breaker reopened after test failure")
                self.circuit_breaker["state"] = CircuitBreakerState.OPEN
                self.circuit_breaker["last_failure_time"] = time.time()
    
    def _check_circuit_breaker(self) -> bool:
        """
        Check if the circuit breaker allows Redis operations.
        
        Returns:
            bool: True if operations are allowed, False otherwise
        """
        if not self.circuit_breaker["config"].enabled:
            return True
            
        if self.circuit_breaker["state"] == CircuitBreakerState.CLOSED:
            return True
            
        if self.circuit_breaker["state"] == CircuitBreakerState.OPEN:
            # Check if enough time has passed to try again
            if (time.time() - self.circuit_breaker["last_failure_time"] >
                    self.circuit_breaker["config"].reset_timeout):
                self.logger.info("Redis circuit breaker entering HALF-OPEN state for testing")
                self.circuit_breaker["state"] = CircuitBreakerState.HALF_OPEN
                return True
            return False
            
        # HALF_OPEN state - allow the operation to test if Redis is back
        return True
    
    def _default_serializer(self, value: Any) -> bytes:
        """Default serialization using pickle."""
        try:
            return pickle.dumps(value)
        except Exception as e:
            self.logger.error(f"Serialization error: {str(e)}")
            raise CacheError(f"Failed to serialize value: {str(e)}")
    
    def _default_deserializer(self, data: bytes) -> Any:
        """Default deserialization using pickle."""
        if data is None:
            return None
            
        try:
            return pickle.loads(data)
        except Exception as e:
            self.logger.error(f"Deserialization error: {str(e)}")
            raise CacheError(f"Failed to deserialize value: {str(e)}")
    
    def _execute_redis_command(self, command_func, *args, **kwargs) -> Any:
        """
        Execute a Redis command with circuit breaker protection.
        
        Args:
            command_func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Any: Result of the Redis command
            
        Raises:
            CacheError: If the circuit is open or the command fails
        """
        if not self._check_circuit_breaker():
            self.logger.warning("Redis circuit breaker is OPEN, skipping operation")
            raise CacheError("Redis circuit breaker is open due to previous failures")
            
        try:
            result = command_func(*args, **kwargs)
            self._update_circuit_breaker(success=True)
            return result
        except RedisError as e:
            self.logger.error(f"Redis operation failed: {str(e)}")
            self._update_circuit_breaker(success=False)
            raise CacheError(f"Redis operation failed: {str(e)}")
    
    def _prepare_key(self, key: str) -> str:
        """
        Prepare a key for use with Redis.
        
        Args:
            key: Original cache key
            
        Returns:
            str: Prepared key
        """
        # Hash keys that might be too long
        if len(key) > 100:
            hash_obj = hashlib.sha256(key.encode())
            return f"hash:{hash_obj.hexdigest()}"
        return key
    
    def _create_metadata(
        self,
        key: str,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        version: Optional[str] = None
    ) -> CacheMetadata:
        """
        Create metadata for a cached item.
        
        Args:
            key: Cache key
            ttl: Time-to-live in seconds
            tags: Set of tags for invalidation
            version: Version string for the cached item
            
        Returns:
            CacheMetadata: Metadata object
        """
        now = datetime.utcnow()
        expires_at = None
        
        if ttl is not None:
            expires_at = now + timedelta(seconds=ttl)
            
        return CacheMetadata(
            key=key,
            created_at=now,
            expires_at=expires_at,
            tags=set(tags or []),
            version=version or "1"
        )
    
    def _create_cached_item(self, value: Any, metadata: CacheMetadata) -> CachedItem:
        """
        Create a cached item with value and metadata.
        
        Args:
            value: Cache value
            metadata: Cache metadata
            
        Returns:
            CachedItem: Cached item object
        """
        return CachedItem(value=value, metadata=metadata)
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        version: Optional[str] = None
    ) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None for default)
            tags: Set of tags for invalidation
            version: Version string for the cached item
            
        Returns:
            bool: True if successful, False otherwise
        """
        prepared_key = self._prepare_key(key)
        
        if ttl is None:
            ttl = self.default_ttl
            
        # Create metadata
        metadata = self._create_metadata(key, ttl, tags, version)
        
        # Create cached item
        cached_item = self._create_cached_item(value, metadata)
        
        # Serialize the cached item
        try:
            serialized_data = self.serializer(cached_item)
        except Exception as e:
            self.logger.error(f"Failed to serialize cached item: {str(e)}")
            return False
        
        # Store in Redis
        try:
            success = self._execute_redis_command(
                self.redis.setex,
                prepared_key,
                ttl,
                serialized_data
            )
            
            # Register tags for this key if successful
            if success and tags:
                for tag in tags:
                    tag_key = f"tag:{tag}"
                    self._execute_redis_command(
                        self.redis.sadd,
                        tag_key,
                        prepared_key
                    )
            
            return bool(success)
        except CacheError:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Any]: Cached value or None if not found
        """
        prepared_key = self._prepare_key(key)
        
        try:
            serialized_data = self._execute_redis_command(
                self.redis.get,
                prepared_key
            )
            
            if not serialized_data:
                return None
                
            # Deserialize the cached item
            cached_item = self.deserializer(serialized_data)
            
            # Check if the item has expired
            if (cached_item.metadata.expires_at and 
                    cached_item.metadata.expires_at < datetime.utcnow()):
                self.logger.debug(f"Cache item '{key}' has expired")
                return None
                
            return cached_item.value
        except CacheError:
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if successful, False otherwise
        """
        prepared_key = self._prepare_key(key)
        
        try:
            # Remove from any tag sets first
            # This is a best-effort operation
            try:
                cached_data = self._execute_redis_command(
                    self.redis.get,
                    prepared_key
                )
                
                if cached_data:
                    cached_item = self.deserializer(cached_data)
                    for tag in cached_item.metadata.tags:
                        tag_key = f"tag:{tag}"
                        self._execute_redis_command(
                            self.redis.srem,
                            tag_key,
                            prepared_key
                        )
            except Exception:
                # Continue even if tag cleanup fails
                pass
            
            # Now delete the key
            result = self._execute_redis_command(
                self.redis.delete,
                prepared_key
            )
            
            return result > 0
        except CacheError:
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if the key exists, False otherwise
        """
        prepared_key = self._prepare_key(key)
        
        try:
            result = self._execute_redis_command(
                self.redis.exists,
                prepared_key
            )
            
            return bool(result)
        except CacheError:
            return False
    
    def add_cache_invalidation(self, rule: InvalidationRule) -> None:
        """
        Add a cache invalidation rule.
        
        Args:
            rule: Invalidation rule
        """
        self.invalidation_rules.append(rule)
        self.logger.info(f"Added cache invalidation rule for tag '{rule.tag}'")
    
    def set_with_tags(
        self,
        key: str,
        value: Any,
        tags: Set[str],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set a value in the cache with tags for invalidation.
        
        Args:
            key: Cache key
            value: Value to cache
            tags: Set of tags for invalidation
            ttl: Time-to-live in seconds (None for default)
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.set(key, value, ttl, tags)
    
    def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all cache entries with the given tag.
        
        Args:
            tag: Tag to invalidate
            
        Returns:
            int: Number of keys invalidated
        """
        tag_key = f"tag:{tag}"
        
        try:
            # Get all keys with this tag
            keys = self._execute_redis_command(
                self.redis.smembers,
                tag_key
            )
            
            if not keys:
                return 0
                
            # Delete all keys
            count = self._execute_redis_command(
                self.redis.delete,
                *keys
            )
            
            # Delete the tag set
            self._execute_redis_command(
                self.redis.delete,
                tag_key
            )
            
            self.logger.info(f"Invalidated {count} keys with tag '{tag}'")
            return count
        except CacheError:
            return 0
    
    def get_with_refresh(
        self,
        key: str,
        refresh_func: Callable[[], Any],
        refresh_config: Optional[RefreshConfig] = None
    ) -> Any:
        """
        Get a value from the cache with background refresh capability.
        
        Args:
            key: Cache key
            refresh_func: Function to call to refresh the cache
            refresh_config: Configuration for refresh behavior
            
        Returns:
            Any: Cached value or newly generated value
        """
        if refresh_config is None:
            refresh_config = RefreshConfig()
            
        prepared_key = self._prepare_key(key)
        
        try:
            # Try to get the cached item
            serialized_data = self._execute_redis_command(
                self.redis.get,
                prepared_key
            )
            
            if not serialized_data:
                # Cache miss - generate new value
                value = refresh_func()
                self.set(key, value)
                return value
                
            # Cache hit - deserialize
            cached_item = self.deserializer(serialized_data)
            
            # Check if refresh is needed
            needs_refresh = False
            
            if refresh_config.enabled and cached_item.metadata.expires_at:
                time_to_expiry = (cached_item.metadata.expires_at - datetime.utcnow()).total_seconds()
                
                if time_to_expiry <= refresh_config.threshold_seconds:
                    needs_refresh = True
            
            # If refresh is needed, either do it in background or synchronously
            if needs_refresh:
                if refresh_config.async_refresh:
                    # Async refresh in background
                    self._schedule_refresh(key, refresh_func, refresh_config)
                else:
                    # Synchronous refresh
                    try:
                        value = refresh_func()
                        self.set(key, value)
                        return value
                    except Exception as e:
                        self.logger.error(f"Synchronous refresh failed: {str(e)}")
                        # Fall back to returning the cached value
            
            return cached_item.value
        except CacheError:
            # On cache failure, generate new value
            try:
                value = refresh_func()
                return value
            except Exception as e:
                self.logger.error(f"Refresh function failed: {str(e)}")
                raise CacheError(f"Failed to refresh cache: {str(e)}")
    
    async def _refresh_task(
        self,
        key: str,
        refresh_func: Callable[[], Any],
        refresh_config: RefreshConfig
    ) -> None:
        """
        Background task for refreshing a cache entry.
        
        Args:
            key: Cache key
            refresh_func: Function to call to refresh the cache
            refresh_config: Configuration for refresh behavior
        """
        self.logger.debug(f"Background refresh started for key '{key}'")
        
        try:
            # Generate new value
            value = refresh_func()
            
            # Update the cache
            success = self.set(key, value)
            
            if success:
                self.logger.debug(f"Background refresh completed for key '{key}'")
            else:
                self.logger.warning(f"Background refresh failed to update cache for key '{key}'")
        except Exception as e:
            self.logger.error(f"Background refresh task failed: {str(e)}")
    
    def _schedule_refresh(
        self,
        key: str,
        refresh_func: Callable[[], Any],
        refresh_config: RefreshConfig
    ) -> None:
        """
        Schedule a background refresh task.
        
        Args:
            key: Cache key
            refresh_func: Function to call to refresh the cache
            refresh_config: Configuration for refresh behavior
        """
        # Create a new task
        task = asyncio.create_task(self._refresh_task(key, refresh_func, refresh_config))
        
        # Add to set of background tasks
        self._bg_tasks.add(task)
        
        # Remove from set when done
        task.add_done_callback(self._bg_tasks.discard)
    
    def cache_health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Redis cache.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Check if Redis is responsive
            start_time = time.time()
            ping_result = self._execute_redis_command(self.redis.ping)
            response_time = time.time() - start_time
            
            # Get memory usage info
            info = self._execute_redis_command(self.redis.info, section="memory")
            
            return {
                "status": "healthy" if ping_result else "degraded",
                "circuit_breaker_state": self.circuit_breaker["state"],
                "response_time_ms": round(response_time * 1000, 2),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "used_memory_peak_human": info.get("used_memory_peak_human", "unknown"),
                "maxmemory_human": info.get("maxmemory_human", "unknown"),
                "maxmemory_policy": info.get("maxmemory_policy", "unknown"),
            }
        except CacheError:
            return {
                "status": "unhealthy",
                "circuit_breaker_state": self.circuit_breaker["state"],
                "response_time_ms": None,
                "error": "Redis connection failed",
            }
    
    # Create a more accessible public API that builds on the private methods
    def __del__(self):
        """Cleanup background tasks on deletion."""
        # Cancel all background tasks
        for task in self._bg_tasks:
            if not task.done():
                task.cancel()


class RedisCacheStrategy(CacheStrategy):
    """Redis implementation of the cache strategy interface."""
    
    def __init__(self, redis_client: RedisCacheClient):
        """
        Initialize the Redis cache strategy.
        
        Args:
            redis_client: Redis cache client
        """
        self.redis = redis_client
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Any]: Cached value or None if not found
        """
        return self.redis.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.redis.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.redis.delete(key)
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if the key exists, False otherwise
        """
        return self.redis.exists(key)
    
    def add_cache_invalidation(self, rule: InvalidationRule) -> None:
        """
        Add a cache invalidation rule.
        
        Args:
            rule: Invalidation rule
        """
        self.redis.add_cache_invalidation(rule)
    
    def set_with_tags(
        self,
        key: str,
        value: Any,
        tags: Set[str],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set a value in the cache with tags for invalidation.
        
        Args:
            key: Cache key
            value: Value to cache
            tags: Set of tags for invalidation
            ttl: Time-to-live in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.redis.set_with_tags(key, value, tags, ttl)
    
    def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all cache entries with the given tag.
        
        Args:
            tag: Tag to invalidate
            
        Returns:
            int: Number of keys invalidated
        """
        return self.redis.invalidate_by_tag(tag)
    
    def get_with_refresh(
        self,
        key: str,
        refresh_func: Callable[[], Any],
        refresh_config: Optional[RefreshConfig] = None
    ) -> Any:
        """
        Get a value from the cache with background refresh capability.
        
        Args:
            key: Cache key
            refresh_func: Function to call to refresh the cache
            refresh_config: Configuration for refresh behavior
            
        Returns:
            Any: Cached value or newly generated value
        """
        return self.redis.get_with_refresh(key, refresh_func, refresh_config)
    
    def cache_health_check(self) -> Dict[str, Any]:
        """
        Check the health of the cache.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return self.redis.cache_health_check()


# Decorator for caching function results
def cached(
    key_prefix: str,
    ttl: Optional[int] = None,
    tags: Optional[Set[str]] = None,
    cache_strategy: Optional[CacheStrategy] = None,
    key_builder: Optional[Callable[..., str]] = None
):
    """
    Decorator for caching function results.
    
    Args:
        key_prefix: Prefix for the cache key
        ttl: Time-to-live in seconds
        tags: Set of tags for invalidation
        cache_strategy: Cache strategy to use
        key_builder: Function to build the cache key
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Skip caching if no cache strategy
            if cache_strategy is None:
                return func(*args, **kwargs)
            
            # Build cache key
            if key_builder:
                key = key_builder(*args, **kwargs)
            else:
                # Default key builder
                try:
                    args_str = ','.join(str(arg) for arg in args)
                    kwargs_str = ','.join(f"{k}={v}" for k, v in kwargs.items())
                    key = f"{key_prefix}:{func.__name__}:{args_str}:{kwargs_str}"
                except Exception:
                    # Fall back to a simpler key if args are not serializable
                    key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_value = cache_strategy.get(key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache the result
            if tags:
                cache_strategy.set_with_tags(key, result, tags, ttl)
            else:
                cache_strategy.set(key, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator


class Enum:
    """Placeholder for the Enum class used in CircuitBreakerState."""
    def __init__(self, value):
        self.value = value