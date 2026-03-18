from jose import jwt
from pydantic import BaseModel

from fastie.core.config.config import Config
from fastie.core.service_containers.service_containers import get_registry


class Jwt:

    @classmethod
    def create_token(cls, data: dict | BaseModel) -> str:
        """
        Create a JWT token with the given data.
        :param data: Dictionary containing user data to encode in the token.
        :return: Encoded JWT token as a string.
        """
        config = get_registry().resolve(Config)

        if isinstance(data, BaseModel):
            data = data.model_dump()
        if not data:
            raise ValueError("Data must be provided to create a token")

        return jwt.encode(data, config.get('JWT_SECRET'), algorithm=config.get('JWT_ALGORITHM'))

    @classmethod
    def decode_token(cls, token: str) -> dict:
        """
        Decode a JWT token and return the payload.
        :param token: JWT token to decode.
        :return: Decoded payload as a dictionary.
        """
        config = get_registry().resolve(Config)
        try:
            return jwt.decode(token, config.get('JWT_SECRET'), algorithms=[config.get('JWT_ALGORITHM')])
        except Exception as e:
            raise ValueError(f"Invalid token: {e}")