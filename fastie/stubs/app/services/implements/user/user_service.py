from fastie.core.decorators.di import service
from app.repositories.interfaces.user.i_user_repository import IUserRepository
from app.schemas.responses.user.user_response_schema import UserResponseSchema
from app.schemas.models.user.user_create_schema import UserCreateSchema
from fastie.services.implements.service import Service
from app.services.interfaces.user.i_user_service import IUserService
from app.schemas.models.user.user_update_schema import UserUpdateSchema
from fastie.core.securities.password import __hash_password__

@service
class UserService(Service, IUserService):
    def __init__(self, repository: IUserRepository):
        super().__init__(repository, UserResponseSchema)

    def create(self, data: UserCreateSchema) -> UserResponseSchema:
        payload = data.model_dump(exclude_unset=True)
        payload["password"] = __hash_password__(payload["password"])
        return super().create(UserCreateSchema(**payload))

    def update(self, id: int, data: UserUpdateSchema) -> UserResponseSchema:
        payload = data.model_dump(exclude_unset=True)
        if payload.get("password"):
            payload["password"] = __hash_password__(payload["password"])
        return super().update(id, UserUpdateSchema(**payload))
