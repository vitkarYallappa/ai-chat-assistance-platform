from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Callable, Iterator
import time
from contextlib import contextmanager

from app.utils.logger import get_logger
from app.utils.exceptions import (
    DatabaseConnectionError,
    DatabaseOperationError,
    DatabaseTransactionError
)

logger = get_logger(__name__)

# Generic type for database connection
T = TypeVar('T')

class DatabaseConnection(Generic[T]):
    """
    Abstract database connection manager.
    
    This class provides a common interface for managing database connections,
    implementing connection pooling, transaction management, and health checks.
    """
    
    def __init__(
        self,
        connection_uri: str,
        database_name: str,
        connection_options: Optional[Dict[str, Any]] = None,
        pool_size: int = 10,
        max_idle_time: int = 60000,
        connect_timeout: int = 30000
    ):
        """
        Initialize the database connection manager.
        
        Args:
            connection_uri: URI for database connection
            database_name: Name of the database to connect to
            connection_options: Additional connection options
            pool_size: Size of the connection pool
            max_idle_time: Maximum time a connection can be idle (ms)
            connect_timeout: Connection timeout (ms)
            
        Raises:
            DatabaseConnectionError: If connection initialization fails
        """
        self.connection_uri = connection_uri
        self.database_name = database_name
        self.connection_options = connection_options or {}
        self.pool_size = pool_size
        self.max_idle_time = max_idle_time
        self.connect_timeout = connect_timeout
        
        # Connection pool (populated by subclasses)
        self._pool = None
        
        # Track connection statistics
        self.stats = {
            "connections_created": 0,
            "connections_closed": 0,
            "transactions_started": 0,
            "transactions_committed": 0,
            "transactions_rolled_back": 0,
            "last_connection_error": None,
            "last_successful_connection": None
        }
        
        try:
            # Initialize the connection pool
            self._initialize_pool()
            logger.info(
                f"Initialized database connection pool for {database_name}",
                extra={
                    "database_name": database_name,
                    "pool_size": pool_size
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize database connection pool: {str(e)}",
                extra={"database_name": database_name}
            )
            self.stats["last_connection_error"] = {
                "timestamp": time.time(),
                "error": str(e)
            }
            raise DatabaseConnectionError(f"Database connection initialization failed: {str(e)}")
    
    @abstractmethod
    def _initialize_pool(self) -> None:
        """
        Initialize the connection pool.
        
        This method should be implemented by subclasses to initialize
        the connection pool specific to the database type.
        
        Raises:
            DatabaseConnectionError: If pool initialization fails
        """
        pass
    
    @abstractmethod
    def get_connection(self) -> T:
        """
        Get a connection from the pool.
        
        Returns:
            A database connection object
            
        Raises:
            DatabaseConnectionError: If connection acquisition fails
        """
        pass
    
    @abstractmethod
    def close_connection(self, connection: T) -> None:
        """
        Return a connection to the pool.
        
        Args:
            connection: Connection to return to the pool
            
        Raises:
            DatabaseConnectionError: If connection release fails
        """
        pass
    
    @contextmanager
    def connection(self) -> Iterator[T]:
        """
        Context manager for database connections.
        
        Yields:
            A database connection from the pool
            
        Raises:
            DatabaseConnectionError: If connection acquisition fails
        """
        connection = None
        try:
            connection = self.get_connection()
            yield connection
        finally:
            if connection:
                self.close_connection(connection)
    
    @abstractmethod
    def execute_transaction(self, operations: Callable[[T], Any]) -> Any:
        """
        Execute operations in a transaction.
        
        Args:
            operations: Callable that takes a connection and performs operations
            
        Returns:
            Result of the operations
            
        Raises:
            DatabaseTransactionError: If transaction fails
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Check database health status.
        
        Returns:
            Dictionary containing health check results
            
        Raises:
            DatabaseConnectionError: If health check fails
        """
        pass
    
    def __del__(self):
        """
        Clean up resources when object is destroyed.
        
        This method attempts to clean up any remaining database connections
        when the connection manager is garbage collected.
        """
        try:
            # Clean up resources, will be implemented by subclasses
            pass
        except Exception as e:
            logger.warning(f"Error during database connection cleanup: {str(e)}")
            
    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection pool statistics.
        
        Returns:
            Dictionary containing connection pool statistics
        """
        return self.stats