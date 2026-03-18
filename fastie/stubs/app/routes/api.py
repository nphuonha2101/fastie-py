from fastapi import FastAPI

from app.api.v1.controllers.auth.auth_controller import AuthController
from app.api.v1.controllers.user_account.user_account_controller import UserAccountController
from fastie.core.route_registrar.route_registra import RouteRegistrar

def register_routes(app: FastAPI):
    """
    Register all application routes with appropriate middleware
    
    Route Types:
    - "public": CORS + Logging + Rate Limiting (for login, register)
    - "protected": public + Authentication (for user data)
    
    For advanced middleware usage, see docs/middleware_usage_guide.md
    """
    route_registrar = RouteRegistrar(app)

    # Auth endpoints (public access)
    route_registrar.register(
        AuthController, 
        prefix="/auth", 
        tags=["Auth"],
        route_type="public"
    )
    
    # User endpoints (protected access)
    route_registrar.register(
        UserAccountController, 
        prefix="/user", 
        tags=["UserAccount"],
        route_type="protected"
    )

    route_registrar.apply()
