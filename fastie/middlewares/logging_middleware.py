import logging
import time
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from fastie.middlewares.abstract_middleware import AbstractMiddleware
from fastie.core.decorators.di import component


@component
class LoggingMiddleware(AbstractMiddleware):
    def __init__(self):
        self.logger = logging.getLogger("api_requests")
        self.logger.setLevel(logging.INFO)
        
        # Create handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    async def handle(self, request: Request, credentials: HTTPAuthorizationCredentials = None):
        """
        Log request information
        """
        start_time = time.time()
        
        # Log request information
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        self.logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"IP: {client_ip} - User-Agent: {user_agent}"
        )
        
        # Save start time to calculate processing time
        request.state.start_time = start_time
        
        return {"logged": True} 