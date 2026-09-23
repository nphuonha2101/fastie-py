from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from fastie.middlewares.abstract_middleware import AbstractMiddleware
from fastie.core.decorators.di import component
from fastie.core.securities.jwt import Jwt


@component
class AuthMiddleware(AbstractMiddleware):
    def __init__(self):
        self.jwt = Jwt

    async def handle(self, request: Request, credentials: HTTPAuthorizationCredentials):
        """
        Handle JWT token authentication
        """
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not provided",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = self.jwt.decode_token(credentials.credentials)
            
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Save user_id to request state to use in controller
            request.state.user_id = user_id
            return {"user_id": user_id}
            
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
