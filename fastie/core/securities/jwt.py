from datetime import datetime, timedelta, timezone

import jwt
from pydantic import BaseModel

from fastie.core.config.config import Config
from fastie.core.service_containers.service_containers import get_registry


class Jwt:

    @staticmethod
    def _settings():
        config = get_registry().resolve(Config)
        secret = config.get('JWT_SECRET') or config.get('SECRET_KEY')
        algorithm = config.get('JWT_ALGORITHM') or config.get('ALGORITHM') or 'HS256'

        insecure_secrets = {
            'your-secret-key',
            'your-secret-key-here',
            'change-me',
            'replace-with-a-random-secret-at-least-32-characters-long',
        }
        if not secret or str(secret) in insecure_secrets or len(str(secret)) < 32:
            raise RuntimeError(
                'JWT_SECRET must be set to a random value of at least 32 characters.'
            )

        if algorithm not in {'HS256', 'HS384', 'HS512'}:
            raise RuntimeError(f'Unsupported JWT algorithm: {algorithm}')

        return str(secret), algorithm, config

    @classmethod
    def create_token(cls, data: dict | BaseModel) -> str:
        """
        Create a JWT token with the given data.
        :param data: Dictionary containing user data to encode in the token.
        :return: Encoded JWT token as a string.
        """
        if isinstance(data, BaseModel):
            data = data.model_dump()
        if not data:
            raise ValueError("Data must be provided to create a token")

        secret, algorithm, config = cls._settings()
        payload = dict(data)
        payload.setdefault(
            'exp',
            datetime.now(timezone.utc) + timedelta(
                minutes=int(config.get('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
            ),
        )
        payload.setdefault('iat', datetime.now(timezone.utc))

        return jwt.encode(payload, secret, algorithm=algorithm)

    @classmethod
    def decode_token(cls, token: str) -> dict:
        """
        Decode a JWT token and return the payload.
        :param token: JWT token to decode.
        :return: Decoded payload as a dictionary.
        """
        secret, algorithm, _ = cls._settings()
        try:
            return jwt.decode(token, secret, algorithms=[algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise ValueError("Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise ValueError("Invalid token") from exc
