from fastie.core.decorators.di import service
from app.repositories.interfaces.user.i_user_repository import IUserRepository
from app.schemas.responses.user.user_response_schema import UserResponseSchema
from fastie.services.implements.service import Service
from app.services.interfaces.user.i_user_service import IUserService

@service
class UserService(Service, IUserService):
    def __init__(self, repository: IUserRepository):
        super().__init__(repository, UserResponseSchema)


