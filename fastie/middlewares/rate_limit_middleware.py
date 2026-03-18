import time
from collections import defaultdict
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from fastie.middlewares.abstract_middleware import AbstractMiddleware
from fastie.core.decorators.di import component


@component
class RateLimitMiddleware(AbstractMiddleware):
    def __init__(self):
        self.request_counts = defaultdict(list)
        self.max_requests = 100  # Max requests
        self.time_window = 3600  # In 1 hour (3600 seconds)

    async def handle(self, request: Request, credentials: HTTPAuthorizationCredentials = None):
        """
        Check rate limit for client
        """
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Get list of request times for client
        client_requests = self.request_counts[client_ip]
        
        # Remove old requests (outside time window)
        client_requests[:] = [
            req_time for req_time in client_requests 
            if current_time - req_time < self.time_window
        ]
        
        # Check if over the limit
        if len(client_requests) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quá nhiều requests. Giới hạn {self.max_requests} requests/{self.time_window}s",
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + self.time_window))
                }
            )
        
        # Add current request
        client_requests.append(current_time)
        
        # Add rate limit information to response headers
        remaining = self.max_requests - len(client_requests)
        request.state.rate_limit_headers = {
            "X-RateLimit-Limit": str(self.max_requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(current_time + self.time_window))
        }
        
        return {"rate_limit": "passed"} 