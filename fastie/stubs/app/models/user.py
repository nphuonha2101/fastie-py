from sqlalchemy import Column, Integer, String, Boolean
from fastie.models.abstract_model import AbstractModel


class User(AbstractModel):
    __tablename__ = 'users'

    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    avatar = Column(String(255), nullable=True)
