"""JWT helpers using PyJWT with explicit claim and algorithm validation."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from pydantic import BaseModel

from fastie.core.config.config import get_config


class Jwt:
    """Small wrapper around the standard PyJWT API."""

    @staticmethod
    def _settings():
        config = get_config()
        secret = config.get("JWT_SECRET") or config.get("SECRET_KEY")
        algorithm = config.get("JWT_ALGORITHM") or "HS256"
        issuer = config.get("JWT_ISSUER")
        audience = config.get("JWT_AUDIENCE")

        insecure_secrets = {
            "your-secret-key",
            "your-secret-key-here",
            "change-me",
            "replace-with-a-random-secret-at-least-32-characters-long",
        }
        if not secret or str(secret) in insecure_secrets or len(str(secret)) < 32:
            raise RuntimeError(
                "JWT_SECRET must be set to a random value of at least 32 characters."
            )

        if algorithm not in {"HS256", "HS384", "HS512"}:
            raise RuntimeError(f"Unsupported JWT algorithm: {algorithm}")

        return str(secret), algorithm, str(issuer) if issuer else None, str(audience) if audience else None, config

    @classmethod
    def create_token(cls, data: dict | BaseModel) -> str:
        if isinstance(data, BaseModel):
            data = data.model_dump()
        if not data:
            raise ValueError("Data must be provided to create a token")

        secret, algorithm, issuer, audience, config = cls._settings()
        now = datetime.now(timezone.utc)
        expires_in = int(config.get("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
        payload = dict(data)
        payload.setdefault("iat", now)
        payload.setdefault("exp", now + timedelta(minutes=expires_in))
        payload.setdefault("jti", str(uuid4()))
        payload.setdefault("typ", "access")
        if issuer:
            payload.setdefault("iss", issuer)
        if audience:
            payload.setdefault("aud", audience)

        return jwt.encode(payload, secret, algorithm=algorithm)

    @classmethod
    def decode_token(cls, token: str) -> dict:
        if not token or not isinstance(token, str):
            raise ValueError("Token must be provided")

        secret, algorithm, issuer, audience, _ = cls._settings()
        decode_kwargs = {
            "algorithms": [algorithm],
            "options": {"require": ["exp", "iat", "sub", "jti"]},
        }
        if issuer:
            decode_kwargs["issuer"] = issuer
        if audience:
            decode_kwargs["audience"] = audience

        try:
            return jwt.decode(token, secret, **decode_kwargs)
        except jwt.PyJWTError as exc:
            raise ValueError("Invalid or expired token") from exc
