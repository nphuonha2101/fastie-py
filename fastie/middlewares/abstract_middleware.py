from abc import ABC, abstractmethod
from fastapi import Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

class AbstractMiddleware(ABC):
    """
    Abstract base class for FastAPI Depends-style middleware.
    """

    @abstractmethod
    async def handle(self, request: Request, credentials: HTTPAuthorizationCredentials):
        """
        Must be implemented by subclass to handle the request.
        """
        pass

    async def __call__(self, request: Request, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        return await self.handle(request, credentials)
