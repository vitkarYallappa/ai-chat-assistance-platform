from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import uuid
from bson import ObjectId
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.domain.models.message import Message
from app.domain.schemas.message import (
    MessageCreate,
    MessageUpdate,
    MessageResponse,
    MessageType
)
from app.domain.interfaces.repository_interface import RepositoryInterface
from app.infrastructure.database.mongodb.client import MongoDBClient
from app.utils.exceptions import (
    RepositoryError,
    EntityNotFoundError,
    DuplicateEntityError,
    ValidationError
)
from app.utils.logger import get_logger
from app.utils.pagination import PaginationParams, PaginatedResult

logger = get_logger(__name__)

class MessageRepository(RepositoryInterface[Message, str]):
    """
    Repository for managing message storage.
    
    This class implements the repository pattern for messages,
    providing methods for creating, retrieving, updating, and deleting
    message records in MongoDB.
    """
    
    def __init__(self, db_client: MongoDBClient):
        """
        Initialize the message repository.
        
        Args:
            db_client: MongoDB client instance
        """
        self.db_client = db_client
        self.collection_name = "messages"
        
        # Ensure indexes for common queries
        self._ensure_indexes()
        
        logger.info(f"Initialized MessageRepository")
    
    def _ensure_indexes(self) -> None:
        """
        Ensure required indexes exist on the messages collection.
        """
        try:
            indexes = [
                # Unique index on message_id
                {
                    "key": {"message_id": 1},
                    "name": "message_id_unique",
                    "unique": True
                },
                # Index for conversation queries (most common access pattern)
                {
                    "key": {"conversation_id": 1, "created_at": 1},
                    "name": "conversation_messages"
                },
                # Index for tenant queries
                {
                    "key": {"tenant_id": 1, "created_at": -1},
                    "name": "tenant_messages"
                },
                # Index for user queries
                {
                    "key": {"user_id": 1, "created_at": -1},
                    "name": "user_messages"
                },
                # Index for message type queries
                {
                    "key": {"message_type": 1, "created_at": -1},
                    "name": "message_type_index"
                },
                # TTL index for auto-deleting old messages (optional)
                # {
                #     "key": {"created_at": 1},
                #     "name": "message_ttl",
                #     "expireAfterSeconds": 30 * 24 * 60 * 60  # 30 days
                # }
            ]
            
            self.db_client.create_indexes(self.collection_name, indexes)
        except Exception as e:
            logger.warning(f"Failed to create indexes for messages: {str(e)}")
    
    def _map_to_model(self, data: Dict[str, Any]) -> Message:
        """
        Map database document to Message model.
        
        Args:
            data: Database document
            
        Returns:
            Message model
        """
        # Remove MongoDB's _id field if present
        if "_id" in data:
            data.pop("_id")
            
        return Message(**data)
    
    def _map_to_document(self, message: Union[Message, MessageCreate]) -> Dict[str, Any]:
        """
        Map Message model to database document.
        
        Args:
            message: Message model or create schema
            
        Returns:
            Database document
        """
        if isinstance(message, Message):
            # Convert model to dict
            document = message.dict()
        else:
            # Convert create schema to dict and add required fields
            document = message.dict()
            document["message_id"] = str(uuid.uuid4())
            document["created_at"] = datetime.utcnow()
            
        return document
    
    def get_by_id(self, message_id: str) -> Message:
        """
        Retrieve message by ID.
        
        Args:
            message_id: Unique identifier for the message
            
        Returns:
            Message model
            
        Raises:
            EntityNotFoundError: If message not found
            RepositoryError: If retrieval fails
        """
        try:
            collection = self.db_client.get_collection(self.collection_name)
            document = collection.find_one({"message_id": message_id})
            
            if not document:
                logger.info(f"Message not found: {message_id}")
                raise EntityNotFoundError(f"Message not found: {message_id}")
                
            logger.debug(f"Retrieved message: {message_id}")
            return self._map_to_model(document)
        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve message {message_id}: {str(e)}")
            raise RepositoryError(f"Failed to retrieve message: {str(e)}")
    
    def create(self, message: MessageCreate) -> Message:
        """
        Create a new message.
        
        Args:
            message: Message creation data
            
        Returns:
            Created message model
            
        Raises:
            DuplicateEntityError: If message ID already exists
            ValidationError: If message data is invalid
            RepositoryError: If creation fails
        """
        try:
            # Map to document
            document = self._map_to_document(message)
            
            # Validate required fields
            if not document.get("conversation_id"):
                raise ValidationError("conversation_id is required")
                
            if not document.get("tenant_id"):
                raise ValidationError("tenant_id is required")
                
            # Insert document
            collection = self.db_client.get_collection(self.collection_name)
            result = collection.insert_one(document)
            
            if not result.acknowledged:
                raise RepositoryError("Failed to create message: operation not acknowledged")
                
            logger.info(
                f"Created message {document['message_id']}",
                extra={
                    "conversation_id": document["conversation_id"],
                    "tenant_id": document["tenant_id"],
                    "message_type": document.get("message_type", "unknown")
                }
            )
            
            return self._map_to_model(document)
        except DuplicateKeyError:
            logger.warning(f"Duplicate message ID: {document.get('message_id')}")
            raise DuplicateEntityError(f"Message ID already exists")
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create message: {str(e)}")
            raise RepositoryError(f"Failed to create message: {str(e)}")
    
    def create_many(self, messages: List[MessageCreate]) -> List[Message]:
        """
        Create multiple messages in batch.
        
        Args:
            messages: List of message creation data
            
        Returns:
            List of created message models
            
        Raises:
            ValidationError: If any message data is invalid
            RepositoryError: If batch creation fails
        """
        if not messages:
            return []
            
        try:
            # Map to documents
            documents = [self._map_to_document(msg) for msg in messages]
            
            # Validate all documents
            for doc in documents:
                if not doc.get("conversation_id"):
                    raise ValidationError("conversation_id is required")
                    
                if not doc.get("tenant_id"):
                    raise ValidationError("tenant_id is required")
            
            # Insert documents
            collection = self.db_client.get_collection(self.collection_name)
            result = collection.insert_many(documents, ordered=False)
            
            if not result.acknowledged:
                raise RepositoryError("Failed to create messages: operation not acknowledged")
                
            logger.info(
                f"Created {len(documents)} messages in batch",
                extra={
                    "conversation_id": documents[0]["conversation_id"],
                    "tenant_id": documents[0]["tenant_id"]
                }
            )
            
            return [self._map_to_model(doc) for doc in documents]
        except DuplicateKeyError as e:
            logger.warning(f"Duplicate message ID in batch: {str(e)}")
            raise DuplicateEntityError(f"Duplicate message ID in batch")
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create messages in batch: {str(e)}")
            raise RepositoryError(f"Failed to create messages in batch: {str(e)}")
    
    def delete(self, message_id: str) -> bool:
        """
        Delete message.
        
        Args:
            message_id: Unique identifier for the message
            
        Returns:
            True if deletion was successful
            
        Raises:
            EntityNotFoundError: If message not found
            RepositoryError: If deletion fails
        """
        try:
            collection = self.db_client.get_collection(self.collection_name)
            result = collection.delete_one({"message_id": message_id})
            
            if result.deleted_count == 0:
                logger.info(f"Message not found for deletion: {message_id}")
                raise EntityNotFoundError(f"Message not found: {message_id}")
                
            logger.info(f"Deleted message {message_id}")
            return True
        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete message {message_id}: {str(e)}")
            raise RepositoryError(f"Failed to delete message: {str(e)}")
    
    def list_by_conversation(
        self,
        conversation_id: str,
        message_type: Optional[MessageType] = None,
        skip_system_messages: bool = False,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Message]:
        """
        List messages in a conversation.
        
        Args:
            conversation_id: Conversation ID
            message_type: Optional message type filter
            skip_system_messages: Whether to exclude system messages
            start_time: Optional start time filter
            end_time: Optional end time filter
            pagination: Pagination parameters
            
        Returns:
            Paginated list of messages
            
        Raises:
            RepositoryError: If listing fails
        """
        try:
            # Build query filter
            query_filter = {"conversation_id": conversation_id}
            
            if message_type:
                query_filter["message_type"] = message_type
                
            if skip_system_messages:
                query_filter["message_type"] = {"$ne": MessageType.SYSTEM}
                
            # Add time filters if provided
            if start_time or end_time:
                query_filter["created_at"] = {}
                
                if start_time:
                    query_filter["created_at"]["$gte"] = start_time
                    
                if end_time:
                    query_filter["created_at"]["$lte"] = end_time
                    
            # Set up pagination
            if not pagination:
                pagination = PaginationParams()
                
            skip = (pagination.page - 1) * pagination.page_size
            limit = pagination.page_size
            
            # Execute query
            collection = self.db_client.get_collection(self.collection_name)
            
            # Get total count for pagination
            total_count = collection.count_documents(query_filter)
            
            # Get paginated results
            cursor = collection.find(query_filter) \
                .sort("created_at", 1) \
                .skip(skip) \
                .limit(limit)
                
            # Convert documents to models
            messages = [self._map_to_model(doc) for doc in cursor]
            
            logger.debug(
                f"Listed {len(messages)} messages for conversation {conversation_id}",
                extra={
                    "message_type": message_type,
                    "skip_system_messages": skip_system_messages,
                    "page": pagination.page,
                    "page_size": pagination.page_size,
                    "total_count": total_count
                }
            )
            
            return PaginatedResult(
                items=messages,
                total=total_count,
                page=pagination.page,
                page_size=pagination.page_size,
                pages=((total_count - 1) // pagination.page_size) + 1 if total_count > 0 else 0
            )
        except Exception as e:
            logger.error(f"Failed to list messages for conversation {conversation_id}: {str(e)}")
            raise RepositoryError(f"Failed to list messages: {str(e)}")
    
    def get_message_count(
        self,
        conversation_id: str,
        message_type: Optional[MessageType] = None,
        skip_system_messages: bool = False
    ) -> int:
        """
        Get message count for a conversation.
        
        Args:
            conversation_id: Conversation ID
            message_type: Optional message type filter
            skip_system_messages: Whether to exclude system messages
            
        Returns:
            Message count
            
        Raises:
            RepositoryError: If count operation fails
        """
        try:
            # Build query filter
            query_filter = {"conversation_id": conversation_id}
            
            if message_type:
                query_filter["message_type"] = message_type
                
            if skip_system_messages:
                query_filter["message_type"] = {"$ne": MessageType.SYSTEM}
                
            # Execute count
            collection = self.db_client.get_collection(self.collection_name)
            count = collection.count_documents(query_filter)
            
            logger.debug(
                f"Counted {count} messages for conversation {conversation_id}",
                extra={
                    "message_type": message_type,
                    "skip_system_messages": skip_system_messages
                }
            )
            
            return count
        except Exception as e:
            logger.error(f"Failed to count messages for conversation {conversation_id}: {str(e)}")
            raise RepositoryError(f"Failed to count messages: {str(e)}")
    
    def delete_by_conversation(self, conversation_id: str) -> int:
        """
        Delete all messages for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Number of deleted messages
            
        Raises:
            RepositoryError: If deletion fails
        """
        try:
            collection = self.db_client.get_collection(self.collection_name)
            result = collection.delete_many({"conversation_id": conversation_id})
            
            deleted_count = result.deleted_count
            
            logger.info(
                f"Deleted {deleted_count} messages for conversation {conversation_id}"
            )
            
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete messages for conversation {conversation_id}: {str(e)}")
            raise RepositoryError(f"Failed to delete messages: {str(e)}")