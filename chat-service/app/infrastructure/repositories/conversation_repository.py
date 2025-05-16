from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import uuid
from bson import ObjectId
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.domain.models.conversation import Conversation
from app.domain.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationStatus
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

class ConversationRepository(RepositoryInterface[Conversation, str]):
    """
    Repository for managing conversation storage.
    
    This class implements the repository pattern for conversations,
    providing methods for creating, retrieving, updating, and deleting
    conversation records in MongoDB.
    """
    
    def __init__(self, db_client: MongoDBClient):
        """
        Initialize the conversation repository.
        
        Args:
            db_client: MongoDB client instance
        """
        self.db_client = db_client
        self.collection_name = "conversations"
        
        # Ensure indexes for common queries
        self._ensure_indexes()
        
        logger.info(f"Initialized ConversationRepository")
    
    def _ensure_indexes(self) -> None:
        """
        Ensure required indexes exist on the conversations collection.
        """
        try:
            indexes = [
                # Unique index on conversation_id
                {
                    "key": {"conversation_id": 1},
                    "name": "conversation_id_unique",
                    "unique": True
                },
                # Index for user queries
                {
                    "key": {"user_id": 1, "created_at": -1},
                    "name": "user_conversations"
                },
                # Index for tenant queries
                {
                    "key": {"tenant_id": 1, "created_at": -1},
                    "name": "tenant_conversations"
                },
                # Compound index for tenant + user queries
                {
                    "key": {"tenant_id": 1, "user_id": 1, "created_at": -1},
                    "name": "tenant_user_conversations"
                },
                # Index for status queries
                {
                    "key": {"status": 1, "updated_at": -1},
                    "name": "status_index"
                },
                # TTL index for auto-deleting old conversations (optional)
                # {
                #     "key": {"updated_at": 1},
                #     "name": "conversation_ttl",
                #     "expireAfterSeconds": 30 * 24 * 60 * 60  # 30 days
                # }
            ]
            
            self.db_client.create_indexes(self.collection_name, indexes)
        except Exception as e:
            logger.warning(f"Failed to create indexes for conversations: {str(e)}")
    
    def _map_to_model(self, data: Dict[str, Any]) -> Conversation:
        """
        Map database document to Conversation model.
        
        Args:
            data: Database document
            
        Returns:
            Conversation model
        """
        # Remove MongoDB's _id field if present
        if "_id" in data:
            data.pop("_id")
            
        return Conversation(**data)
    
    def _map_to_document(self, conversation: Union[Conversation, ConversationCreate]) -> Dict[str, Any]:
        """
        Map Conversation model to database document.
        
        Args:
            conversation: Conversation model or create schema
            
        Returns:
            Database document
        """
        if isinstance(conversation, Conversation):
            # Convert model to dict
            document = conversation.dict()
        else:
            # Convert create schema to dict and add required fields
            document = conversation.dict()
            document["conversation_id"] = str(uuid.uuid4())
            document["created_at"] = datetime.utcnow()
            document["updated_at"] = document["created_at"]
            document["status"] = ConversationStatus.ACTIVE
            
        return document
    
    def get_by_id(self, conversation_id: str) -> Conversation:
        """
        Retrieve conversation by ID.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            Conversation model
            
        Raises:
            EntityNotFoundError: If conversation not found
            RepositoryError: If retrieval fails
        """
        try:
            collection = self.db_client.get_collection(self.collection_name)
            document = collection.find_one({"conversation_id": conversation_id})
            
            if not document:
                logger.info(f"Conversation not found: {conversation_id}")
                raise EntityNotFoundError(f"Conversation not found: {conversation_id}")
                
            logger.debug(f"Retrieved conversation: {conversation_id}")
            return self._map_to_model(document)
        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve conversation {conversation_id}: {str(e)}")
            raise RepositoryError(f"Failed to retrieve conversation: {str(e)}")
    
    def create(self, conversation: ConversationCreate) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            conversation: Conversation creation data
            
        Returns:
            Created conversation model
            
        Raises:
            DuplicateEntityError: If conversation ID already exists
            ValidationError: If conversation data is invalid
            RepositoryError: If creation fails
        """
        try:
            # Map to document
            document = self._map_to_document(conversation)
            
            # Validate required fields
            if not document.get("tenant_id"):
                raise ValidationError("tenant_id is required")
                
            if not document.get("user_id"):
                raise ValidationError("user_id is required")
                
            # Insert document
            collection = self.db_client.get_collection(self.collection_name)
            result = collection.insert_one(document)
            
            if not result.acknowledged:
                raise RepositoryError("Failed to create conversation: operation not acknowledged")
                
            logger.info(
                f"Created conversation {document['conversation_id']}",
                extra={
                    "tenant_id": document["tenant_id"],
                    "user_id": document["user_id"]
                }
            )
            
            return self._map_to_model(document)
        except DuplicateKeyError:
            logger.warning(f"Duplicate conversation ID: {document.get('conversation_id')}")
            raise DuplicateEntityError(f"Conversation ID already exists")
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create conversation: {str(e)}")
            raise RepositoryError(f"Failed to create conversation: {str(e)}")
    
    def update(self, conversation_id: str, conversation: ConversationUpdate) -> Conversation:
        """
        Update conversation state.
        
        Args:
            conversation_id: Unique identifier for the conversation
            conversation: Updated conversation data
            
        Returns:
            Updated conversation model
            
        Raises:
            EntityNotFoundError: If conversation not found
            RepositoryError: If update fails
        """
        try:
            # Get update data
            update_data = conversation.dict(exclude_unset=True)
            
            # Always update the updated_at timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            # Perform update
            collection = self.db_client.get_collection(self.collection_name)
            result = collection.update_one(
                {"conversation_id": conversation_id},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                logger.info(f"Conversation not found for update: {conversation_id}")
                raise EntityNotFoundError(f"Conversation not found: {conversation_id}")
                
            if result.modified_count == 0:
                logger.debug(f"Update had no effect on conversation {conversation_id}")
                
            # Retrieve updated conversation
            updated_conversation = self.get_by_id(conversation_id)
            
            logger.info(
                f"Updated conversation {conversation_id}",
                extra={
                    "modified_count": result.modified_count,
                    "fields_updated": list(update_data.keys())
                }
            )
            
            return updated_conversation
        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update conversation {conversation_id}: {str(e)}")
            raise RepositoryError(f"Failed to update conversation: {str(e)}")
    
    def delete(self, conversation_id: str) -> bool:
        """
        Delete conversation.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            True if deletion was successful
            
        Raises:
            EntityNotFoundError: If conversation not found
            RepositoryError: If deletion fails
        """
        try:
            collection = self.db_client.get_collection(self.collection_name)
            result = collection.delete_one({"conversation_id": conversation_id})
            
            if result.deleted_count == 0:
                logger.info(f"Conversation not found for deletion: {conversation_id}")
                raise EntityNotFoundError(f"Conversation not found: {conversation_id}")
                
            logger.info(f"Deleted conversation {conversation_id}")
            return True
        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {str(e)}")
            raise RepositoryError(f"Failed to delete conversation: {str(e)}")
    
    def list_by_user(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        status: Optional[ConversationStatus] = None,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Conversation]:
        """
        List conversations for a user.
        
        Args:
            user_id: User ID
            tenant_id: Optional tenant ID filter
            status: Optional conversation status filter
            pagination: Pagination parameters
            
        Returns:
            Paginated list of conversations
            
        Raises:
            RepositoryError: If listing fails
        """
        try:
            # Build query filter
            query_filter = {"user_id": user_id}
            
            if tenant_id:
                query_filter["tenant_id"] = tenant_id
                
            if status:
                query_filter["status"] = status
                
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
                .sort("created_at", -1) \
                .skip(skip) \
                .limit(limit)
                
            # Convert documents to models
            conversations = [self._map_to_model(doc) for doc in cursor]
            
            logger.debug(
                f"Listed {len(conversations)} conversations for user {user_id}",
                extra={
                    "tenant_id": tenant_id,
                    "status": status,
                    "page": pagination.page,
                    "page_size": pagination.page_size,
                    "total_count": total_count
                }
            )
            
            return PaginatedResult(
                items=conversations,
                total=total_count,
                page=pagination.page,
                page_size=pagination.page_size,
                pages=((total_count - 1) // pagination.page_size) + 1 if total_count > 0 else 0
            )
        except Exception as e:
            logger.error(f"Failed to list conversations for user {user_id}: {str(e)}")
            raise RepositoryError(f"Failed to list conversations: {str(e)}")
    
    def list_by_tenant(
        self,
        tenant_id: str,
        status: Optional[ConversationStatus] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Conversation]:
        """
        List conversations for a tenant.
        
        Args:
            tenant_id: Tenant ID
            status: Optional conversation status filter
            from_date: Optional start date filter
            to_date: Optional end date filter
            pagination: Pagination parameters
            
        Returns:
            Paginated list of conversations
            
        Raises:
            RepositoryError: If listing fails
        """
        try:
            # Build query filter
            query_filter = {"tenant_id": tenant_id}
            
            if status:
                query_filter["status"] = status
                
            # Add date filters if provided
            if from_date or to_date:
                query_filter["created_at"] = {}
                
                if from_date:
                    query_filter["created_at"]["$gte"] = from_date
                    
                if to_date:
                    query_filter["created_at"]["$lte"] = to_date
                    
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
                .sort("created_at", -1) \
                .skip(skip) \
                .limit(limit)
                
            # Convert documents to models
            conversations = [self._map_to_model(doc) for doc in cursor]
            
            logger.debug(
                f"Listed {len(conversations)} conversations for tenant {tenant_id}",
                extra={
                    "status": status,
                    "page": pagination.page,
                    "page_size": pagination.page_size,
                    "total_count": total_count
                }
            )
            
            return PaginatedResult(
                items=conversations,
                total=total_count,
                page=pagination.page,
                page_size=pagination.page_size,
                pages=((total_count - 1) // pagination.page_size) + 1 if total_count > 0 else 0
            )
        except Exception as e:
            logger.error(f"Failed to list conversations for tenant {tenant_id}: {str(e)}")
            raise RepositoryError(f"Failed to list conversations: {str(e)}")