"""Authentication and session routes."""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from fastie.core.securities.jwt import Jwt
from fastie.core.securities.password import verify_password_and_upgrade
from fastie.infrastructures.database.dependencies import get_db
from fastie.middlewares.rate_limit_middleware import RateLimitMiddleware
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.requests.refresh_token.refresh_token_request_schema import (
    RefreshTokenRequestSchema,
)
from app.schemas.responses.user.user_response_schema import UserResponseSchema


logger = logging.getLogger(__name__)
auth_router = APIRouter(prefix="/auth", tags=["Auth"])
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


async def auth_rate_limit_with_headers(request: Request, response: Response):
    """Apply auth rate limiting and expose standard response headers."""
    result = await _get_auth_rate_limiter().handle(request)
    response.headers.update(getattr(request.state, "rate_limit_headers", {}))
    return result


async def close_auth_rate_limiter():
    """Release the shared Redis client when the app shuts down."""
    if _get_auth_rate_limiter.cache_info().currsize:
        await _get_auth_rate_limiter().close()


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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _refresh_token_expiry() -> datetime:
    from fastie.core.config.config import get_config

    days = int(get_config().get("REFRESH_TOKEN_EXPIRE_DAYS", 30))
    return _utc_now() + timedelta(days=days)


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_refresh_token(
    user_id: int,
    db: Session,
    family_id: str | None = None,
) -> str:
    raw_token = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            user_id=user_id,
            family_id=family_id or str(uuid4()),
            token_hash=_hash_refresh_token(raw_token),
            expires_at=_refresh_token_expiry(),
        )
    )
    return raw_token


def _revoke_refresh_token_family(family_id: str, db: Session) -> None:
    active_tokens = db.query(RefreshToken).filter(
        RefreshToken.family_id == family_id,
        RefreshToken.revoked_at.is_(None),
    ).with_for_update().all()
    revoked_at = _utc_now()
    for token in active_tokens:
        token.revoked_at = revoked_at


def _access_token(user: User, scopes: list[str] | None = None) -> str:
    return Jwt.create_token({
        "sub": str(user.id),
        "email": user.email,
        "scope": " ".join(scopes or []),
    })


def _issue_token(
    email: str,
    password: str,
    db: Session,
    scopes: list[str] | None = None,
):
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

    refresh_token = _create_refresh_token(user.id, db)
    access_token = _access_token(user, scopes)
    db.commit()
    return user, access_token, refresh_token


@auth_router.post("/token", summary="OAuth2 Access Token")
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    _: dict = Depends(auth_rate_limit_with_headers),
):
    _, access_token, refresh_token = _issue_token(
        form_data.username,
        form_data.password,
        db,
        form_data.scopes,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@auth_router.post("/refresh", summary="Refresh Access Token")
def refresh(
    request: RefreshTokenRequestSchema,
    db: Session = Depends(get_db),
    _: dict = Depends(auth_rate_limit_with_headers),
):
    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == _hash_refresh_token(request.refresh_token))
        .with_for_update()
        .first()
    )
    if stored_token is None:
        raise _unauthorized("Invalid or expired refresh token")
    if stored_token.revoked_at is not None:
        logger.warning(
            "Refresh token reuse detected user_id=%s family_id=%s",
            stored_token.user_id,
            stored_token.family_id,
        )
        _revoke_refresh_token_family(stored_token.family_id, db)
        db.commit()
        raise _unauthorized("Refresh token reuse detected")
    if stored_token.expires_at <= _utc_now():
        raise _unauthorized("Invalid or expired refresh token")

    user = (
        db.query(User)
        .filter(
            User.id == stored_token.user_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        .first()
    )
    if user is None:
        raise _unauthorized("User is no longer active")

    stored_token.revoked_at = _utc_now()
    new_refresh_token = _create_refresh_token(
        user.id,
        db,
        family_id=stored_token.family_id,
    )
    access_token = _access_token(user)
    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@auth_router.post("/logout", status_code=204, summary="Revoke Refresh Token")
def logout(
    request: RefreshTokenRequestSchema,
    db: Session = Depends(get_db),
    _: dict = Depends(auth_rate_limit_with_headers),
):
    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == _hash_refresh_token(request.refresh_token))
        .first()
    )
    if stored_token is not None and stored_token.revoked_at is None:
        stored_token.revoked_at = _utc_now()
        db.commit()
    return None


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
