from abc import ABC

from app.models.user import User
from fastie.repositories.interfaces.i_repository import IRepository
from app.schemas.models.user.user_create_schema import UserCreateSchema
from app.schemas.models.user.user_update_schema import UserUpdateSchema


class IUserRepository(IRepository[User, UserCreateSchema, UserUpdateSchema], ABC):
    pass
