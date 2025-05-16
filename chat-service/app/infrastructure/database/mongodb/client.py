from typing import Any, Dict, List, Optional, Union, Callable, Iterator
import time
from contextlib import contextmanager
from urllib.parse import quote_plus

import pymongo
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import (
    ConnectionFailure,
    OperationFailure,
    ServerSelectionTimeoutError,
    NetworkTimeout,
    ConfigurationError
)

from app.infrastructure.database.connection import DatabaseConnection
from app.utils.logger import get_logger
from app.utils.exceptions import (
    DatabaseConnectionError,
    DatabaseOperationError,
    DatabaseTransactionError,
    DatabaseConfigError
)

logger = get_logger(__name__)

class MongoDBClient(DatabaseConnection[MongoClient]):
    """
    MongoDB client implementation.
    
    This class provides a MongoDB-specific implementation of the DatabaseConnection
    interface, including connection pooling, transaction management, and health checks.
    """
    
    def __init__(
        self,
        connection_uri: str = "",
        database_name: str = "",
        host: str = "localhost",
        port: int = 27017,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auth_source: str = "admin",
        auth_mechanism: str = "SCRAM-SHA-256",
        pool_size: int = 10,
        max_idle_time: int = 60000,
        connect_timeout: int = 30000,
        server_selection_timeout: int = 30000,
        replica_set: Optional[str] = None,
        ssl: bool = False,
        ssl_cert_reqs: Optional[str] = None,
        ssl_ca_certs: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize MongoDB client.
        
        Args:
            connection_uri: MongoDB connection URI (if provided, other connection params are ignored)
            database_name: Name of the database to connect to
            host: MongoDB host
            port: MongoDB port
            username: Username for authentication
            password: Password for authentication
            auth_source: Authentication source database
            auth_mechanism: Authentication mechanism
            pool_size: Size of the connection pool
            max_idle_time: Maximum time a connection can be idle (ms)
            connect_timeout: Connection timeout (ms)
            server_selection_timeout: Server selection timeout (ms)
            replica_set: Replica set name
            ssl: Whether to use SSL
            ssl_cert_reqs: SSL certificate requirements
            ssl_ca_certs: SSL CA certificates
            **kwargs: Additional connection options
            
        Raises:
            DatabaseConnectionError: If connection initialization fails
            DatabaseConfigError: If configuration is invalid
        """
        # Store MongoDB-specific connection options
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.auth_source = auth_source
        self.auth_mechanism = auth_mechanism
        self.server_selection_timeout = server_selection_timeout
        self.replica_set = replica_set
        self.ssl = ssl
        self.ssl_cert_reqs = ssl_cert_reqs
        self.ssl_ca_certs = ssl_ca_certs
        
        # Build connection URI if not provided
        if not connection_uri:
            connection_uri = self._build_connection_uri()
        
        # Additional MongoDB-specific options
        connection_options = {
            "maxPoolSize": pool_size,
            "maxIdleTimeMS": max_idle_time,
            "connectTimeoutMS": connect_timeout,
            "serverSelectionTimeoutMS": server_selection_timeout,
            "retryWrites": True,
            **kwargs
        }
        
        if replica_set:
            connection_options["replicaSet"] = replica_set
            
        if ssl:
            connection_options["ssl"] = ssl
            if ssl_cert_reqs:
                connection_options["ssl_cert_reqs"] = ssl_cert_reqs
            if ssl_ca_certs:
                connection_options["ssl_ca_certs"] = ssl_ca_certs
        
        # Initialize base class
        super().__init__(
            connection_uri=connection_uri,
            database_name=database_name,
            connection_options=connection_options,
            pool_size=pool_size,
            max_idle_time=max_idle_time,
            connect_timeout=connect_timeout
        )
    
    def _build_connection_uri(self) -> str:
        """
        Build MongoDB connection URI from connection parameters.
        
        Returns:
            MongoDB connection URI
        """
        if self.username and self.password:
            auth_string = f"{quote_plus(self.username)}:{quote_plus(self.password)}@"
        else:
            auth_string = ""
            
        uri = f"mongodb://{auth_string}{self.host}:{self.port}"
        
        # Add query parameters
        query_params = []
        
        if self.auth_source:
            query_params.append(f"authSource={self.auth_source}")
            
        if self.auth_mechanism:
            query_params.append(f"authMechanism={self.auth_mechanism}")
            
        if query_params:
            uri += "?" + "&".join(query_params)
            
        return uri
    
    def _initialize_pool(self) -> None:
        """
        Initialize MongoDB connection pool.
        
        Raises:
            DatabaseConnectionError: If pool initialization fails
        """
        try:
            # Create MongoDB client
            self._client = MongoClient(
                self.connection_uri,
                **self.connection_options
            )
            
            # Verify connection by pinging the database
            self._client.admin.command('ping')
            
            # Update stats
            self.stats["last_successful_connection"] = time.time()
            logger.info("Successfully connected to MongoDB")
        except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError) as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            self.stats["last_connection_error"] = {
                "timestamp": time.time(),
                "error": str(e)
            }
            raise DatabaseConnectionError(f"MongoDB connection failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {str(e)}")
            self.stats["last_connection_error"] = {
                "timestamp": time.time(),
                "error": str(e)
            }
            raise DatabaseConnectionError(f"Unexpected MongoDB connection error: {str(e)}")
    
    def get_connection(self) -> MongoClient:
        """
        Get MongoDB client.
        
        Returns:
            MongoDB client
            
        Raises:
            DatabaseConnectionError: If client acquisition fails
        """
        try:
            if not self._client:
                self._initialize_pool()
                
            return self._client
        except Exception as e:
            logger.error(f"Failed to get MongoDB connection: {str(e)}")
            raise DatabaseConnectionError(f"Failed to get MongoDB connection: {str(e)}")
    
    def close_connection(self, connection: MongoClient) -> None:
        """
        Return MongoDB client to pool.
        
        In MongoDB's Python driver, connections are automatically returned to
        the pool, so this method is a no-op.
        
        Args:
            connection: MongoDB client
        """
        # No-op, as MongoDB's Python driver handles connection pooling internally
        pass
    
    def get_database(self) -> Database:
        """
        Get MongoDB database instance.
        
        Returns:
            MongoDB database instance
            
        Raises:
            DatabaseConnectionError: If database acquisition fails
        """
        try:
            return self.get_connection()[self.database_name]
        except Exception as e:
            logger.error(f"Failed to get MongoDB database: {str(e)}")
            raise DatabaseConnectionError(f"Failed to get MongoDB database: {str(e)}")
    
    def get_collection(self, collection_name: str) -> Collection:
        """
        Get MongoDB collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            MongoDB collection
            
        Raises:
            DatabaseConnectionError: If collection acquisition fails
        """
        try:
            return self.get_database()[collection_name]
        except Exception as e:
            logger.error(f"Failed to get MongoDB collection: {str(e)}")
            raise DatabaseConnectionError(f"Failed to get MongoDB collection: {str(e)}")
    
    @contextmanager
    def session(self):
        """
        Context manager for MongoDB sessions.
        
        Yields:
            A MongoDB session
        
        Raises:
            DatabaseConnectionError: If session creation fails
        """
        session = None
        try:
            session = self.get_connection().start_session()
            yield session
        except Exception as e:
            logger.error(f"MongoDB session error: {str(e)}")
            raise DatabaseConnectionError(f"MongoDB session error: {str(e)}")
        finally:
            if session:
                session.end_session()
    
    def execute_transaction(self, operations: Callable[[MongoClient], Any]) -> Any:
        """
        Execute operations in a MongoDB transaction.
        
        Args:
            operations: Callable that takes a client and performs operations
            
        Returns:
            Result of the operations
            
        Raises:
            DatabaseTransactionError: If transaction fails
        """
        client = self.get_connection()
        
        # Check if transactions are supported (requires replica set)
        if not self.replica_set:
            logger.warning("MongoDB transactions require a replica set, executing without transaction")
            try:
                return operations(client)
            except Exception as e:
                logger.error(f"MongoDB operation error: {str(e)}")
                raise DatabaseOperationError(f"MongoDB operation error: {str(e)}")
        
        # Start a session and run operations in a transaction
        with client.start_session() as session:
            self.stats["transactions_started"] += 1
            try:
                result = session.with_transaction(
                    lambda s: operations(client),
                    read_concern=pymongo.read_concern.ReadConcern("majority"),
                    write_concern=pymongo.write_concern.WriteConcern("majority")
                )
                self.stats["transactions_committed"] += 1
                return result
            except (OperationFailure, NetworkTimeout) as e:
                self.stats["transactions_rolled_back"] += 1
                logger.error(f"MongoDB transaction failed: {str(e)}")
                raise DatabaseTransactionError(f"MongoDB transaction failed: {str(e)}")
            except Exception as e:
                self.stats["transactions_rolled_back"] += 1
                logger.error(f"Unexpected error in MongoDB transaction: {str(e)}")
                raise DatabaseTransactionError(f"Unexpected MongoDB transaction error: {str(e)}")
    
    def create_indexes(self, collection_name: str, indexes: List[Dict[str, Any]]) -> List[str]:
        """
        Create indexes for a MongoDB collection.
        
        Args:
            collection_name: Name of the collection
            indexes: List of index specifications
            
        Returns:
            List of created index names
            
        Raises:
            DatabaseOperationError: If index creation fails
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.create_indexes(indexes)
            logger.info(
                f"Created indexes for collection {collection_name}",
                extra={"index_count": len(indexes)}
            )
            return result
        except Exception as e:
            logger.error(f"Failed to create indexes for collection {collection_name}: {str(e)}")
            raise DatabaseOperationError(f"Failed to create indexes: {str(e)}")
    
    def ping(self) -> bool:
        """
        Test connection to MongoDB.
        
        Returns:
            True if connection is successful
            
        Raises:
            DatabaseConnectionError: If connection test fails
        """
        try:
            self.get_connection().admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB ping failed: {str(e)}")
            raise DatabaseConnectionError(f"MongoDB ping failed: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check MongoDB health status.
        
        Returns:
            Dictionary containing health check results
            
        Raises:
            DatabaseConnectionError: If health check fails
        """
        try:
            start_time = time.time()
            
            # Get MongoDB server info
            client = self.get_connection()
            server_info = client.server_info()
            
            # Get database stats
            db_stats = self.get_database().command("dbStats")
            
            # Calculate response time
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "version": server_info.get("version", "unknown"),
                "storage_size": db_stats.get("storageSize", 0),
                "collections": db_stats.get("collections", 0),
                "indexes": db_stats.get("indexes", 0),
                "connection_pool": {
                    "pool_size": self.pool_size,
                    "max_idle_time_ms": self.max_idle_time
                },
                "stats": self.get_stats()
            }
        except Exception as e:
            logger.error(f"MongoDB health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "stats": self.get_stats()
            }
    
    def __del__(self):
        """Clean up resources when object is destroyed."""
        try:
            if hasattr(self, '_client') and self._client:
                self._client.close()
                logger.debug("Closed MongoDB client connection")
        except Exception as e:
            logger.warning(f"Error closing MongoDB client: {str(e)}")