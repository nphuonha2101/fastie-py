from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Literal

from sqlalchemy.orm import Session

T = TypeVar("T")
TCreate = TypeVar("TCreate")
TUpdate = TypeVar("TUpdate")

class IRepository(ABC, Generic[T, TCreate, TUpdate]):
    @abstractmethod
    def set_session(self, session: Session):
        """Set the SQLAlchemy session for database operations."""
        pass


    @abstractmethod
    def get_all(
            self,
            skip: int = 0,
            limit: int = 100,
            order_by: Optional[str] = None,
            order_direction: Literal["asc", "desc"] = "asc",
            with_trash: bool = False,
            eager_relations: Optional[List[str]] = None,
    ) -> List[T]:
        """
        Retrieve all records with optional pagination and sorting.
        """
        pass

    @abstractmethod
    def get_by_id(
            self,
            id: int,
            with_trash: bool = False,
            eager_relations: Optional[List[str]] = None,
    ) -> Optional[T]:
        """Retrieve a single record by ID."""
        pass

    @abstractmethod
    def create(self, data: TCreate) -> T:
        """Create a new record."""
        pass

    @abstractmethod
    def update(self, id: int, data: TUpdate) -> T:
        """Update an existing record by ID."""
        pass

    @abstractmethod
    def delete(self, id: int) -> None:
        """
        Soft delete a record by ID.
        :param id: id of the record to delete
        :return:  None
        """
        pass


    @abstractmethod
    def force_delete(self, id: int) -> None:
        """Delete a record by ID."""
        pass

    @abstractmethod
    def restore(self, id: int) -> T:
        """Restore a soft-deleted record by ID."""
        pass
