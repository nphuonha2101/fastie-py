from typing import Any

from fastie.core.securities.jwt import Jwt
from fastie.core.securities.password import __verify_password__
from fastie.infrastructures.database.db_context import DbContext

class Auth:
    @classmethod
    def authenticate(cls, model, credentials: dict):
        """
        Authenticate a user based on the provided credentials.
        :param model: The database model to query (e.g., User).
        :param credentials: A dictionary containing the user's credentials. Example: { "email": "example.com", "password": "your_password" }
        :return: Dictionary with user data if authentication succeeds, None otherwise
        """
        password = credentials.pop("password", None)
        if password is None:
            raise ValueError("Password field is required in credentials")

        with DbContext() as db:
            query = db.session.query(model)
            for field, value in credentials.items():
                if hasattr(model, field):
                    query = query.filter(getattr(model, field) == value)
                else:
                    raise AttributeError(f"{model.__name__} has no attribute '{field}'")

            user = query.first()
            if not user or not __verify_password__(password, user.password):
                return None

            if isinstance(user, model) and hasattr(user, 'get_response_model'):
                return user.get_response_model().model_validate(user)
            else:
                return None


    @classmethod
    def create_access_token(cls, user_data: dict) -> str:
        """
        Create an access token for the authenticated user.
        :param user_data: Dictionary containing user data (id, email, name).
        :return: A JWT token as a string.
        """
        if not user_data:
            raise ValueError("User data must be provided to create an access token")

        return Jwt.create_token(user_data)

    @classmethod
    def decode_session_token(cls, model, token: str) -> dict[str, Any] | None:
        """
        Decode a JWT token to retrieve user data.
        :param token: JWT token as a string.
        :return: Dictionary with user data if the token is valid, None otherwise.
        """
        if not token:
            raise ValueError("Token must be provided for decoding")

        try:
            with DbContext() as db:
                query = db.session.query(model)
                if hasattr(model, "token"):
                    query = query.filter(getattr(model, "token") == token)
                else:
                    query = query.filter(getattr(model, "id") == token)

                user = query.first()

                if isinstance(user, model) and hasattr(user, 'get_response_model'):
                    return user.get_response_model().model_validate(user)
        except Exception as e:
            raise ValueError(f"Error decoding token: {str(e)}")
