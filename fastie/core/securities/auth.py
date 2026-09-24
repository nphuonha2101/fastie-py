"""Compatibility authentication helpers.

New routes should use a request-scoped ``Session`` dependency and call the
functions in this module with that session. The class methods remain for
existing Fastie applications that still use the legacy service layer.
"""

from typing import Any

from fastie.core.securities.jwt import Jwt
from fastie.core.securities.password import __verify_password__
from fastie.infrastructures.database.dependencies import get_database


def authenticate_user(db, model, credentials: dict):
    """Return an ORM user when credentials are valid, otherwise ``None``."""
    credentials = dict(credentials)
    password = credentials.pop("password", None)
    if password is None:
        raise ValueError("Password field is required in credentials")

    query = db.query(model)
    for field, value in credentials.items():
        if not hasattr(model, field):
            raise AttributeError(f"{model.__name__} has no attribute '{field}'")
        query = query.filter(getattr(model, field) == value)

    if hasattr(model, "is_active"):
        query = query.filter(model.is_active.is_(True))
    if hasattr(model, "deleted_at"):
        query = query.filter(model.deleted_at.is_(None))

    user = query.first()
    if user is None or not __verify_password__(password, user.password):
        return None
    return user


class Auth:
    @classmethod
    def authenticate(cls, model, credentials: dict):
        """Legacy adapter returning the model's response schema."""
        with get_database().get_session() as db:
            user = authenticate_user(db, model, credentials)
            if user is None:
                return None
            if hasattr(user, "get_response_model"):
                return user.get_response_model().model_validate(user)
            return user

    @classmethod
    def create_access_token(cls, user_data: dict) -> str:
        return Jwt.create_token(user_data)

    @classmethod
    def decode_session_token(cls, model, token: str) -> dict[str, Any] | None:
        if not token:
            raise ValueError("Token must be provided for decoding")

        payload = Jwt.decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError("Token subject is missing")

        with get_database().get_session() as db:
            query = db.query(model).filter(model.id == int(user_id))
            if hasattr(model, "is_active"):
                query = query.filter(model.is_active.is_(True))
            if hasattr(model, "deleted_at"):
                query = query.filter(model.deleted_at.is_(None))
            user = query.first()
            if user is None:
                return None
            if hasattr(user, "get_response_model"):
                return user.get_response_model().model_validate(user)
            return user
