from abc import ABC
import jwt
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status

from fastie.controllers.base_controller import BaseController
from fastie.core.decorators.di import controller, inject

@controller
class AuthController(BaseController, ABC):

    def __init__(self):
        super().__init__()
        self.secret_key = "your-secret-key"  # Nên lấy từ environment
        self.algorithm = "HS256"

    def define_routes(self):
        self.router.post("/login", summary="User Login", status_code=200)(self.login)
        self.router.get("/profile", summary="User Profile", status_code=200)(self.get_profile)
        self.router.get("/greet", summary="Greeting Endpoint", status_code=200)(self.greet)

    def login(self, request: Request):
        """
        Handles user login và tạo JWT token.
        :param request: FastAPI Request object
        :return: Success message với JWT token.
        """
        user_data = {
            "user_id": "123",
            "username": "demo_user",
            "email": "demo@example.com"
        }
        
        # generate token - DEMO
        token_data = {
            "sub": user_data["user_id"],
            "username": user_data["username"],
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        access_token = jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)
        
        middleware_info = {}
        if hasattr(request.state, 'rate_limit_headers'):
            middleware_info['rate_limit'] = request.state.rate_limit_headers
        
        return self.success(content={
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_data,
            "middleware_info": middleware_info
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
        
        user_id = request.state.user_id
        
        # Simulated user data - thực tế sẽ query từ database
        user_profile = {
            "user_id": user_id,
            "username": "demo_user",
            "email": "demo@example.com",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        return self.success(content={
            "message": "Profile retrieved successfully",
            "user": user_profile
        })

    def greet(self, request: Request):
        """
        Handles greeting với thông tin từ middleware.
        :param request: FastAPI Request object
        :return: Greeting message với middleware data.
        """
        # Lấy thông tin từ middleware
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




