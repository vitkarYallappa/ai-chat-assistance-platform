import copy
import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Pattern

from app.core.exceptions import CacheError
from app.core.logging import get_logger
from app.adapters.interfaces.cache import CacheStrategy

logger = get_logger(__name__)

class CacheItem:
    """Class representing a cached item with expiration."""
    
    def __init__(self, value: Any, expires_at: Optional[float] = None):
        """
        Initialize a cache item.
        
        Args:
            value: Cached value
            expires_at: Expiration timestamp
        """
        self.value = value
        self.expires_at = expires_at
    
    def is_expired(self) -> bool:
        """
        Check if the item has expired.
        
        Returns:
            True if expired
        """
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

class MemoryCache(CacheStrategy):
    """In-memory implementation of the CacheStrategy interface."""
    
    def __init__(self, default_ttl: int = 300, cleanup_interval: int = 60):
        """
        Initialize the in-memory cache.
        
        Args:
            default_ttl: Default TTL in seconds
            cleanup_interval: Interval for expired items cleanup in seconds
        """
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        
        # Dict to store cache items
        self._cache: Dict[str, CacheItem] = {}
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        logger.info("In-memory cache initialized")
    
    def _start_cleanup_thread(self):
        """Start a background thread to clean up expired items."""
        def cleanup_task():
            while True:
                try:
                    self._cleanup_expired()
                except Exception as e:
                    logger.error(f"Error in cache cleanup thread: {str(e)}")
                time.sleep(self.cleanup_interval)
                
        # Create and start daemon thread
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
        logger.debug(f"Started cache cleanup thread with interval {self.cleanup_interval}s")
    
    def _cleanup_expired(self):
        """Clean up expired cache items."""
        with self._lock:
            current_time = time.time()
            keys_to_delete = []
            
            # Find expired keys
            for key, item in self._cache.items():
                if item.is_expired():
                    keys_to_delete.append(key)
            
            # Delete expired keys
            for key in keys_to_delete:
                del self._cache[key]
                
            if keys_to_delete:
                logger.debug(f"Cleaned up {len(keys_to_delete)} expired cache items")
    
    def _build_key(self, key: str, tenant_id: Optional[str] = None) -> str:
        """
        Build a cache key with optional tenant namespace.
        
        Args:
            key: Original key
            tenant_id: Optional tenant ID for multi-tenant keys
            
        Returns:
            Namespaced key
        """
        if tenant_id:
            return f"{tenant_id}:{key}"
        return key
    
    async def get(self, key: str, tenant_id: Optional[str] = None) -> Any:
        """
        Get item from cache.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID
            
        Returns:
            Cached value or None if not found or expired
        """
        full_key = self._build_key(key, tenant_id)
        
        with self._lock:
            # Check if key exists
            item = self._cache.get(full_key)
            
            # Return None if key not found
            if item is None:
                logger.debug(f"Cache miss for key: {full_key}")
                return None
                
            # Check if item has expired
            if item.is_expired():
                # Remove expired item
                del self._cache[full_key]
                logger.debug(f"Cache miss (expired) for key: {full_key}")
                return None
                
            # Return deep copy of value to prevent mutations
            logger.debug(f"Cache hit for key: {full_key}")
            return copy.deepcopy(item.value)
    
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
        """
        full_key = self._build_key(key, tenant_id)
        effective_ttl = ttl if ttl is not None else self.default_ttl
        
        # Calculate expiration time
        expires_at = None
        if effective_ttl > 0:
            expires_at = time.time() + effective_ttl
            
        # Create cache item
        item = CacheItem(
            value=copy.deepcopy(value),
            expires_at=expires_at
        )
        
        # Store item in cache
        with self._lock:
            self._cache[full_key] = item
            
        logger.debug(f"Set cache key {full_key} with TTL {effective_ttl}s")
        return True
    
    async def delete(self, key: str, tenant_id: Optional[str] = None) -> bool:
        """
        Remove item from cache.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID
            
        Returns:
            True if key was found and deleted
        """
        full_key = self._build_key(key, tenant_id)
        
        with self._lock:
            # Check if key exists
            if full_key in self._cache:
                # Delete key
                del self._cache[full_key]
                logger.debug(f"Deleted cache key: {full_key}")
                return True
            
            logger.debug(f"Key not found for deletion: {full_key}")
            return False
    
    async def exists(self, key: str, tenant_id: Optional[str] = None) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID
            
        Returns:
            True if key exists and has not expired
        """
        full_key = self._build_key(key, tenant_id)
        
        with self._lock:
            # Check if key exists
            item = self._cache.get(full_key)
            
            # Return False if key not found
            if item is None:
                return False
                
            # Check if item has expired
            if item.is_expired():
                # Remove expired item
                del self._cache[full_key]
                return False
                
            return True
    
    async def flush(self, tenant_id: Optional[str] = None) -> int:
        """
        Clear all cache for tenant.
        
        Args:
            tenant_id: Optional tenant ID
            
        Returns:
            Number of keys cleared
        """
        with self._lock:
            if tenant_id:
                # Clear only tenant-specific keys
                prefix = f"{tenant_id}:"
                keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
                
                # Delete matching keys
                for key in keys_to_delete:
                    del self._cache[key]
                    
                count = len(keys_to_delete)
                logger.info(f"Flushed {count} keys for tenant {tenant_id}")
                return count
            else:
                # Clear all keys
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Flushed all {count} keys from cache")
                return count
    
    async def get_keys(self, pattern: str, tenant_id: Optional[str] = None) -> List[str]:
        """
        Get keys matching pattern.
        
        Args:
            pattern: Key pattern (wildcard matching not supported, use case-sensitive substring matching)
            tenant_id: Optional tenant ID
            
        Returns:
            List of matching keys
        """
        with self._lock:
            # Build prefix for tenant keys
            prefix = f"{tenant_id}:" if tenant_id else ""
            
            # Find matching keys
            matching_keys = []
            for key in self._cache.keys():
                # Skip expired items
                item = self._cache[key]
                if item.is_expired():
                    continue
                    
                # Filter by tenant prefix
                if tenant_id and not key.startswith(prefix):
                    continue
                    
                # Remove tenant prefix to get original key
                original_key = key[len(prefix):] if tenant_id else key
                
                # Match pattern as substring
                if pattern in original_key:
                    matching_keys.append(original_key)
            
            logger.debug(f"Found {len(matching_keys)} keys matching pattern '{pattern}'")
            return matching_keys