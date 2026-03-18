from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, Integer, func, DateTime

from fastie.infrastructures.database.database_infrastructure import Base

class AbstractModel(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    def get_response_model(self) -> Optional[BaseModel]:
        """
        Returns the response model for the current model.
        This method should be overridden in subclasses to provide the specific response model.
        """
        raise NotImplementedError("Subclasses must implement this method.")