from abc import ABC

from fastie.controllers.base_controller import BaseController
from fastie.core.decorators.di import controller, inject
from app.schemas.models.user.user_create_schema import UserCreateSchema
from app.schemas.responses.user.user_response_schema import UserResponseSchema
from app.services.interfaces.user.i_user_service import IUserService

@controller
@inject
class UserAccountController(BaseController, ABC):
    def __init__(self, user_service: IUserService):
        super().__init__()
        self.user_service = user_service

    def define_routes(self):
        self.router.get("/", summary="Get All Users", response_model=list[UserResponseSchema], status_code=200)(self.index)
        self.router.post("/register", summary="Register User", response_model=UserResponseSchema, status_code=200)(self.register_user)

    def index(self):
        try:
            users = self.user_service.get_all()
            return self.success(content=users, message="Users retrieved successfully.")
        except Exception as e:
            return self.error(message=str(e))

    def register_user(self, request: UserCreateSchema):
        """
        Register a new user account.
        :param request: UserCreateSchema containing user details.
        :return: Response indicating success or failure.
        """
        try:
            user = self.user_service.create(request)
            return self.success(content=user, message="User registered successfully.")
        except Exception as e:
            return self.error(message=str(e))
