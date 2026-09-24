"""Compose versioned API routers under the ``/api`` namespace."""

from fastapi import APIRouter

from app.routes.auth import (
    auth_rate_limit_with_headers,
    close_auth_rate_limiter,
    get_current_user,
    greet,
    logout,
    profile,
    refresh,
    token,
)
from app.routes.users import list_users, register_user, user_router
from app.routes.v1 import v1_router

# Fastie version routes - generated imports

api_router = APIRouter(prefix="/api")
api_router.include_router(v1_router)
# Fastie version routes - generated includes


def register_routes(app):
    """Attach the versioned API router to a FastAPI instance."""
    app.include_router(api_router)


__all__ = [
    "api_router",
    "auth_rate_limit_with_headers",
    "close_auth_rate_limiter",
    "get_current_user",
    "greet",
    "list_users",
    "logout",
    "profile",
    "refresh",
    "register_routes",
    "register_user",
    "token",
    "user_router",
    "v1_router",
]
