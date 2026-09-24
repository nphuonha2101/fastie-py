import time
import hashlib
import ipaddress
import logging
import os
from collections import defaultdict
from fastapi import HTTPException, status
from starlette.requests import Request

class RateLimitMiddleware:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.request_counts = defaultdict(list)
        self.max_requests = self._positive_int_env("RATE_LIMIT_MAX_REQUESTS", 100)
        self.time_window = self._positive_int_env("RATE_LIMIT_WINDOW_SECONDS", 3600)
        self.redis = None
        self.trusted_proxy_networks = self._proxy_networks()

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

    async def handle(self, request: Request):
        """Check the request rate limit and store headers on the request."""
        client_ip = self._client_ip(request)
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

    async def close(self):
        """Close the Redis connection pool during application shutdown."""
        if self.redis is not None:
            await self.redis.aclose()

    def _client_ip(self, request: Request) -> str:
        peer = request.client.host if request.client else "unknown"
        if peer == "unknown" or not self._is_trusted_proxy(peer):
            return peer

        forwarded_for = request.headers.get("X-Forwarded-For", "")
        candidate = forwarded_for.split(",", 1)[0].strip()
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            return peer
        return candidate

    def _is_trusted_proxy(self, address: str) -> bool:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            return False
        return any(parsed in network for network in self.trusted_proxy_networks)

    @staticmethod
    def _proxy_networks():
        configured = os.getenv("TRUSTED_PROXY_IPS", "")
        networks = []
        for raw_value in configured.split(","):
            value = raw_value.strip()
            if not value:
                continue
            try:
                networks.append(ipaddress.ip_network(value, strict=False))
            except ValueError as exc:
                raise RuntimeError(f"Invalid TRUSTED_PROXY_IPS value: {value}") from exc
        return networks

    @staticmethod
    def _positive_int_env(name: str, default: int) -> int:
        value = os.getenv(name)
        parsed = default if value in (None, "") else int(value)
        if parsed <= 0:
            raise RuntimeError(f"{name} must be greater than zero")
        return parsed
