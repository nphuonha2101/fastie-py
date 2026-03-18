from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Literal

T = TypeVar("T")
TCreate = TypeVar("TCreate")
TUpdate = TypeVar("TUpdate")
TResponse = TypeVar("TResponse")

class IService(ABC, Generic[T, TCreate, TUpdate, TResponse]):
    @abstractmethod
    def get_all(
            self,
            skip: int = 0,
            limit: int = 100,
            order_by: Optional[str] = None,
            order_direction: Literal["asc", "desc"] = "asc"
    ) -> List[T]:
        """
        Retrieve all records with optional pagination and sorting.
        """
        pass

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[TResponse]:
        """Retrieve a single record by ID."""
        pass

    @abstractmethod
    def create(self, data: TCreate) -> TResponse:
        """Create a new record."""
        pass

    @abstractmethod
    def update(self, id: int, data: TUpdate) -> TResponse:
        """Update an existing record by ID."""
        pass

    @abstractmethod
    def delete(self, id: int) -> None:
        """Delete a record by ID. (Soft delete)"""
        pass

    @abstractmethod
    def force_delete(self, id: int) -> None:
        """Delete a record by ID."""
        pass
