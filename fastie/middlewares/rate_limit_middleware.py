import time
import hashlib
import logging
import os
from collections import defaultdict
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from fastie.middlewares.abstract_middleware import AbstractMiddleware
from fastie.core.decorators.di import component


@component
class RateLimitMiddleware(AbstractMiddleware):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.request_counts = defaultdict(list)
        self.max_requests = 100  # Max requests
        self.time_window = 3600  # In 1 hour (3600 seconds)
        self.redis = None

        redis_url = os.getenv("REDIS_URL")
        environment = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower()
        if redis_url:
            try:
                from redis.asyncio import Redis
            except ImportError as exc:
                raise RuntimeError("redis is required when REDIS_URL is configured") from exc
            self.redis = Redis.from_url(redis_url, decode_responses=True)
        elif environment in {"prod", "production"}:
            raise RuntimeError("REDIS_URL must be configured for production rate limiting")

    async def handle(self, request: Request, credentials: HTTPAuthorizationCredentials = None):
        """
        Check rate limit for client
        """
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        if self.redis:
            try:
                client_key = hashlib.sha256(client_ip.encode()).hexdigest()
                redis_key = f"fastie:rate-limit:{client_key}"
                request_count = await self.redis.incr(redis_key)
                if request_count == 1:
                    await self.redis.expire(redis_key, self.time_window)
                reset_after = await self.redis.ttl(redis_key)
            except Exception as exc:
                self.logger.exception("Rate-limit backend unavailable")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Rate limiting service unavailable",
                ) from exc
        else:
            # Development fallback only. Production requires Redis above so
            # limits remain shared across workers and application instances.
            client_requests = self.request_counts[client_ip]
            client_requests[:] = [
                req_time for req_time in client_requests
                if current_time - req_time < self.time_window
            ]
            request_count = len(client_requests) + 1
            client_requests.append(current_time)
            reset_after = self.time_window

        if request_count > self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Limit {self.max_requests} requests/{self.time_window}s",
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + max(reset_after, 0)))
                }
            )

        # Add rate limit information to response headers
        remaining = self.max_requests - request_count
        request.state.rate_limit_headers = {
            "X-RateLimit-Limit": str(self.max_requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(current_time + max(reset_after, 0)))
        }
        
        return {"rate_limit": "passed"}
