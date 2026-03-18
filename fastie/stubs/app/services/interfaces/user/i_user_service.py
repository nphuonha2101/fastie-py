from abc import ABC

from app.models.user import User
from app.schemas.models.user.user_create_schema import UserCreateSchema
from app.schemas.responses.user.user_response_schema import UserResponseSchema
from app.schemas.models.user.user_update_schema import UserUpdateSchema
from fastie.services.interfaces.i_service import IService


class IUserService(IService[User, UserCreateSchema, UserUpdateSchema, UserResponseSchema], ABC):
    pass