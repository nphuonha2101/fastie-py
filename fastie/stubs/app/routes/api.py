"""Application routes.

This is deliberately ordinary FastAPI code. Controllers and the legacy DI
stack are still available, but a new project does not need them for its first
endpoint.
"""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastie.core.securities.jwt import Jwt
from fastie.core.securities.password import (
    __hash_password__,
    verify_password_and_upgrade,
)
from fastie.infrastructures.database.dependencies import get_db
from fastie.middlewares.rate_limit_middleware import RateLimitMiddleware
from app.models.user import User
from app.schemas.models.user.user_create_schema import UserCreateSchema
from app.schemas.requests.access_token.access_token_request_schema import AccessTokenRequestSchema
from app.schemas.responses.user.user_response_schema import UserResponseSchema


api_router = APIRouter(prefix="/api/v1")
auth_router = APIRouter(prefix="/auth", tags=["Auth"])
user_router = APIRouter(prefix="/user", tags=["User"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def _success(data=None, message="Success", status_code=200):
    return {
        "status_code": status_code,
        "success": True,
        "status": "success",
        "message": message,
        "data": data,
    }


def _unauthorized(detail="Invalid or missing token"):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@lru_cache(maxsize=1)
def _get_auth_rate_limiter() -> RateLimitMiddleware:
    return RateLimitMiddleware()


async def auth_rate_limit(request: Request):
    """Protect credential endpoints without coupling them to the DI registry."""
    return await _get_auth_rate_limiter().handle(request)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the active user from the bearer token for protected routes."""
    try:
        payload = Jwt.decode_token(token)
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise _unauthorized()

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        .first()
    )
    if user is None:
        raise _unauthorized("User is no longer active")
    return user


def _issue_token(email: str, password: str, db: Session, scopes: list[str] | None = None):
    user = (
        db.query(User)
        .filter(
            User.email == email,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        .first()
    )
    if user is None:
        raise _unauthorized("Invalid email or password")

    valid_password, upgraded_hash = verify_password_and_upgrade(password, user.password)
    if not valid_password:
        raise _unauthorized("Invalid email or password")
    if upgraded_hash:
        user.password = upgraded_hash
        db.commit()

    token = Jwt.create_token({
        "sub": str(user.id),
        "email": user.email,
        "scope": " ".join(scopes or []),
    })
    return user, token


@auth_router.post(
    "/token",
    summary="OAuth2 Access Token",
    dependencies=[Depends(auth_rate_limit)],
)
def token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    _, access_token = _issue_token(
        form_data.username,
        form_data.password,
        db,
        form_data.scopes,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post(
    "/login",
    summary="User Login",
    dependencies=[Depends(auth_rate_limit)],
)
def login(request: AccessTokenRequestSchema, db: Session = Depends(get_db)):
    user, access_token = _issue_token(request.email, request.password, db)
    return _success(
        data={
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponseSchema.model_validate(user),
        },
        message="Login successful",
    )


@auth_router.get("/profile", summary="User Profile")
def profile(current_user: User = Depends(get_current_user)):
    return _success(
        data={
            "message": "Profile retrieved successfully",
            "user": UserResponseSchema.model_validate(current_user),
        },
        message="Profile retrieved successfully",
    )


@auth_router.get("/greet", summary="Greeting Endpoint")
def greet():
    return _success(message="Hello, welcome to the API!")


@user_router.post(
    "/register",
    summary="Register User",
    status_code=201,
    dependencies=[Depends(auth_rate_limit)],
)
def register_user(request: UserCreateSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == request.email).first() is not None:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(
        **request.model_dump(exclude_unset=True, exclude={"password"}),
        password=__hash_password__(request.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered") from exc
    db.refresh(user)

    return _success(
        data=UserResponseSchema.model_validate(user),
        message="User registered successfully",
        status_code=201,
    )


@user_router.get("/", summary="Get All Users")
def list_users(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    users = (
        db.query(User)
        .filter(User.is_active.is_(True), User.deleted_at.is_(None))
        .order_by(User.id)
        .all()
    )
    return _success(
        data=[UserResponseSchema.model_validate(user) for user in users],
        message="Users retrieved successfully",
    )


api_router.include_router(auth_router)
api_router.include_router(user_router)

# Fastie resource routes - generated imports

# Fastie resource routes - generated includes


def register_routes(app):
    """Attach the application router to a FastAPI instance."""
    app.include_router(api_router)
