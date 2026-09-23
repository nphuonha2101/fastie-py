import datetime
from contextvars import ContextVar
from typing import TypeVar, Generic, Optional, List, Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, inspect

from fastie.repositories.interfaces.i_repository import IRepository

T = TypeVar('T')
TCreate = TypeVar('TCreate')
TUpdate = TypeVar('TUpdate')

class Repository(IRepository[T, TCreate, TUpdate], Generic[T, TCreate, TUpdate]):

    def __init__(self, model_class):
        self.model_class = model_class
        self._session: ContextVar[Optional[Session]] = ContextVar(
            f"repository_session_{id(self)}", default=None
        )

    @property
    def session(self) -> Session:
        session = self._session.get()
        if session is None:
            raise RuntimeError("A database session must be assigned before repository use")
        return session

    def set_session(self, session: Session):
        """
        Set the SQLAlchemy session for database operations.
        This method should be called before any database operations.
        """
        self._session.set(session)


    def get_all(
            self,
            skip: int = 0,
            limit: int = 100,
            order_by: Optional[str] = None,
            order_direction: Literal["asc", "desc"] = "asc",
            with_trash: bool = False,
            eager_relations: Optional[List[str]] = None,
    ) -> List[T]:
        if skip < 0:
            raise ValueError("skip must be greater than or equal to zero")
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")

        query = self.session.query(self.model_class)

        if eager_relations:
            for relation in eager_relations:
                query = query.options(joinedload(getattr(self.model_class, relation)))

        if not with_trash and hasattr(self.model_class, 'deleted_at'):
            query = query.filter(self.model_class.deleted_at.is_(None))

        if order_by:
            if order_by not in inspect(self.model_class).columns:
                raise ValueError(f"Unsupported order_by field: {order_by}")
            column = getattr(self.model_class, order_by)
            query = query.order_by(desc(column) if order_direction == "desc" else asc(column))

        return query.offset(skip).limit(limit).all()


    def get_by_id(
            self,
            id: int,
            with_trash: bool = False,
            eager_relations: Optional[List[str]] = None,
    ) -> Optional[T]:
        query = self.session.query(self.model_class).filter(self.model_class.id == id)

        if eager_relations:
            for relation in eager_relations:
                query = query.options(joinedload(getattr(self.model_class, relation)))

        if not with_trash and hasattr(self.model_class, 'deleted_at'):
            query = query.filter(self.model_class.deleted_at.is_(None))

        return query.first()



    def create(self, data: TCreate) -> T:
        try:
            # Get raw data from model
            if hasattr(data, 'model_dump'):
                raw_data = data.model_dump(exclude_unset=True)
            else:
                raw_data = data.dict(exclude_unset=True)

            # Filter valid columns
            mapper = inspect(self.model_class)
            valid_keys = {c.key for c in mapper.columns}
            item_data = {k: v for k, v in raw_data.items() if k in valid_keys}

            # The surrounding DbContext owns the transaction. This keeps
            # multi-repository service operations atomic.
            db_item = self.model_class(**item_data)
            self.session.add(db_item)
            self.session.flush()

            self.session.refresh(db_item)
            return db_item

        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Integrity error: {str(e)}")
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error creating item: {str(e)}")

    def update(self, id: int, data: TUpdate) -> T:
        try:
            db_item = self.get_by_id(id)
            if db_item is None:
                raise ValueError(f"Item with id {id} not found")

            # Get raw data from model
            if hasattr(data, 'model_dump'):
                raw_data = data.model_dump(exclude_unset=True)
            elif hasattr(data, 'dict'):
                raw_data = data.dict(exclude_unset=True)
            else:
                raw_data = data

            # Filter valid columns
            mapper = inspect(self.model_class)
            valid_keys = {c.key for c in mapper.columns}
            item_data = {k: v for k, v in raw_data.items() if k in valid_keys}

            # The surrounding DbContext owns the transaction. This keeps
            # multi-repository service operations atomic.
            for key, value in item_data.items():
                setattr(db_item, key, value)
            self.session.flush()

            self.session.refresh(db_item)
            return db_item

        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Integrity error: {str(e)}")
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error updating item: {str(e)}")

    def delete(self, id: int) -> None:
        db_item = self.get_by_id(id)
        if db_item is None:
            raise ValueError(f"Item with id {id} not found")
        db_item.deleted_at = datetime.datetime.now()
        self.session.flush()

    def force_delete(self, id: int) -> None:
        db_item = self.get_by_id(id, with_trash=True)
        if db_item is None:
            raise ValueError(f"Item with id {id} not found")

        self.session.delete(db_item)
        self.session.flush()

    def restore(self, id: int) -> T:
        db_item = self.get_by_id(id, with_trash=True)
        if db_item is None:
            raise ValueError(f"Item with id {id} not found")

        if hasattr(db_item, 'deleted_at'):
            db_item.deleted_at = None
            self.session.flush()
            self.session.refresh(db_item)
        
        return db_item
