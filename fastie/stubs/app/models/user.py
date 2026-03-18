from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Boolean
from fastie.models.abstract_model import AbstractModel
from app.schemas.responses.user.user_response_schema import UserResponseSchema


class User(AbstractModel):
    __tablename__ = 'users'

    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    avatar = Column(String(255), nullable=True)
    token = Column(String(255), nullable=True)

    def get_response_model(self) -> Optional[BaseModel]:
        return UserResponseSchema

