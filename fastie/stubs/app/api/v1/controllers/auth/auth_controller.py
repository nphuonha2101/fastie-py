from abc import ABC
from fastapi import Depends, HTTPException, Request, status

from fastie.controllers.base_controller import BaseController
from fastie.core.decorators.di import controller, inject
from fastie.core.securities.auth import Auth
from fastie.infrastructures.database.db_context import DbContext
from fastie.middlewares.auth.auth_middleware import AuthMiddleware
from app.models.user import User
from app.schemas.requests.access_token.access_token_request_schema import AccessTokenRequestSchema
from app.schemas.responses.user.user_response_schema import UserResponseSchema

@controller
class AuthController(BaseController, ABC):

    def __init__(self):
        super().__init__()

    def define_routes(self):
        self.router.post("/login", summary="User Login", status_code=200)(self.login)
        self.router.get(
            "/profile",
            summary="User Profile",
            status_code=200,
            dependencies=[Depends(AuthMiddleware())],
        )(self.get_profile)
        self.router.get("/greet", summary="Greeting Endpoint", status_code=200)(self.greet)

    def login(self, request: AccessTokenRequestSchema):
        """
        Handles user login and creates JWT token.
        :param request: FastAPI Request object
        :return: Success message with JWT token.
        """
        user = Auth.authenticate(User, request.model_dump())
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = Auth.create_access_token({
            "sub": str(user.id),
            "email": str(user.email),
        })
        
        return self.success(content={
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
        })

    def get_profile(self, request: Request):
        """
        Get user profile
        :param request: FastAPI Request object
        :return: User profile
        """
        if not hasattr(request.state, 'user_id'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        try:
            user_id = int(request.state.user_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            ) from exc

        with DbContext() as db:
            user = (
                db.session.query(User)
                .filter(User.id == user_id, User.is_active.is_(True), User.deleted_at.is_(None))
                .first()
            )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is no longer active",
            )

        return self.success(content={
            "message": "Profile retrieved successfully",
            "user": UserResponseSchema.model_validate(user),
        })

    def greet(self, request: Request):
        """
        Handles greeting with information from middleware.
        :param request: FastAPI Request object
        :return: Greeting message with middleware data.
        """
        # Get information from middleware
        client_ip = request.client.host if request.client else "unknown"
        
        middleware_data = {}
        if hasattr(request.state, 'rate_limit_headers'):
            middleware_data['rate_limit'] = request.state.rate_limit_headers
        if hasattr(request.state, 'start_time'):
            middleware_data['logged_at'] = request.state.start_time
        
        return self.success(content={
            "message": "Hello, welcome to the API!",
            "client_ip": client_ip,
            "middleware_data": middleware_data
        })



