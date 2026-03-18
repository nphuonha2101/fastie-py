from typing import TypeVar, Generic, Optional, List, Literal

from pydantic import BaseModel

from fastie.core.exceptions.repository_exception import RepositoryException
from fastie.infrastructures.database.db_context import DbContext
from fastie.repositories.interfaces.i_repository import IRepository
from fastie.services.interfaces.i_service import IService

T = TypeVar('T')
TCreate = TypeVar('TCreate')
TUpdate = TypeVar('TUpdate')
TResponse = TypeVar('TResponse', bound=BaseModel)

class Service(IService[T, TCreate, TUpdate, TResponse], Generic[T, TCreate, TUpdate, TResponse]):
    def __init__(self, repository: IRepository[T, TCreate, TUpdate], response_model: Optional[BaseModel] = None):
        self.repository = repository
        self.response_model = response_model

    def get_all(
            self,
            skip: int = 0,
            limit: int = 100,
            order_by: Optional[str] = None,
            order_direction: Literal["asc", "desc"] = "asc"
    ) -> List[T]:
        try:
            with DbContext() as db_context:
                self.repository.set_session(db_context.session)
                # Call the repository method to get all records
                if order_by is not None and order_direction not in ["asc", "desc"]:
                    raise ValueError("order_direction must be 'asc' or 'desc'")

                # Return the result from the repository
                items = self.repository.get_all(skip, limit, order_by, order_direction)
                return [self.response_model.model_validate(item) for item in items]
        except Exception as e:
            raise RepositoryException('Error retrieving records: ' + str(e))

    def get_by_id(self, id: int) -> Optional[T]:
        try:
            with DbContext() as db_context:
                self.repository.set_session(db_context.session)
                return self.response_model.model_validate(self.repository.get_by_id(id))
        except Exception as e:
            raise RepositoryException('Error retrieving record by ID: ' + str(e))

    def create(self, data: TCreate) -> T:
        try:
            with DbContext() as db_context:
                self.repository.set_session(db_context.session)
                return self.response_model.model_validate(self.repository.create(data))
        except Exception as e:
            raise RepositoryException('Error creating record: ' + str(e))

    def update(self, id: int, data: TUpdate) -> T:
        try:
            with DbContext() as db_context:
                self.repository.set_session(db_context.session)
                return self.response_model.model_validate(self.repository.update(id, data))
        except Exception as e:
            raise RepositoryException('Error updating record: ' + str(e))

    def delete(self, id: int) -> None:
        try:
            with DbContext() as db_context:
                self.repository.set_session(db_context.session)
                return self.repository.delete(id)
        except Exception as e:
            raise RepositoryException('Error deleting record: ' + str(e))

    def force_delete(self, id: int) -> None:
        try:
            with DbContext() as db_context:
                self.repository.set_session(db_context.session)
                return self.repository.force_delete(id)
        except Exception as e:
            raise RepositoryException('Error deleting record: ' + str(e))