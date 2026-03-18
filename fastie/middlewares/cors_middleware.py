from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request
from starlette.responses import Response

from fastie.middlewares.abstract_middleware import AbstractMiddleware
from fastie.core.decorators.di import component


@component
class CORSMiddleware(AbstractMiddleware):
    def __init__(self):
        self.allowed_origins = ["*"]  # Should be configured in environment
        self.allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = ["*"]

    async def handle(self, request: Request, credentials: HTTPAuthorizationCredentials = None):
        """
        Handle CORS headers
        :param request: FastAPI Request object
        :param credentials: HTTP Authorization credentials
        :return: CORS headers
        """
        # Bypass for preflight OPTIONS requests
        if request.method == "OPTIONS":
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = ", ".join(self.allowed_origins)
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
            response.headers["Access-Control-Max-Age"] = "3600"
            return response

        # Add CORS headers to state for response
        if not hasattr(request.state, 'cors_headers'):
            request.state.cors_headers = {
                "Access-Control-Allow-Origin": ", ".join(self.allowed_origins),
                "Access-Control-Allow-Methods": ", ".join(self.allowed_methods),
                "Access-Control-Allow-Headers": ", ".join(self.allowed_headers)
            }
        
        return {"cors": "enabled"} 