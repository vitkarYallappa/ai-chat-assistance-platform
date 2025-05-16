from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any, Union
from uuid import UUID

T = TypeVar('T')  # Generic type for the entity
K = TypeVar('K')  # Generic type for the entity ID (usually UUID)

class RepositoryInterface(Generic[T, K], ABC):
    """
    Generic repository interface defining standard CRUD operations.
    Following the Repository pattern to abstract data access.
    """
    
    @abstractmethod
    async def get(self, id: K) -> Optional[T]:
        """
        Retrieves an entity by its ID.
        
        Args:
            id: The ID of the entity to retrieve
            
        Returns:
            The entity if found, None otherwise
            
        Raises:
            RepositoryException: If data access fails
        """
        pass
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """
        Creates a new entity.
        
        Args:
            entity: The entity to create
            
        Returns:
            The created entity with any generated fields (e.g., ID)
            
        Raises:
            RepositoryException: If entity creation fails
        """
        pass
    
    @abstractmethod
    async def update(self, id: K, data: Dict[str, Any]) -> Optional[T]:
        """
        Updates an existing entity.
        
        Args:
            id: The ID of the entity to update
            data: Dictionary of fields to update
            
        Returns:
            The updated entity if found, None otherwise
            
        Raises:
            RepositoryException: If entity update fails
        """
        pass
    
    @abstractmethod
    async def delete(self, id: K) -> bool:
        """
        Deletes an entity by its ID.
        
        Args:
            id: The ID of the entity to delete
            
        Returns:
            True if the entity was deleted, False if not found
            
        Raises:
            RepositoryException: If entity deletion fails
        """
        pass
    
    @abstractmethod
    async def list(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_desc: bool = False
    ) -> List[T]:
        """
        Lists entities with filtering, pagination, and sorting.
        
        Args:
            filters: Optional dictionary of filter conditions
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            sort_by: Field to sort by
            sort_desc: Whether to sort in descending order
            
        Returns:
            List of entities matching the criteria
            
        Raises:
            RepositoryException: If listing fails
        """
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Counts entities matching the given filters.
        
        Args:
            filters: Optional dictionary of filter conditions
            
        Returns:
            Count of matching entities
            
        Raises:
            RepositoryException: If counting fails
        """
        pass