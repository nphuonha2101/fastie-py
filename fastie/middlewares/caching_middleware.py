import hashlib
import json
import time
from typing import Dict, Any, Optional
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from fastie.middlewares.abstract_middleware import AbstractMiddleware
from fastie.core.decorators.di import component


@component
class CachingMiddleware(AbstractMiddleware):
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = 300  # 5 minutes
        self.max_cache_size = 1000  # Max cache size
        self.cacheable_methods = ["GET"]
        self.cacheable_status_codes = [200, 201]
        
        # Patterns không cache
        self.no_cache_patterns = [
            "/auth/",  # Auth endpoints
            "/admin/", # Admin endpoints  
            "private"  
        ]

    def _generate_cache_key(self, request: Request) -> str:
        """
        Tạo cache key từ request
        """
        # Generate cache key from request
        key_data = {
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params),
        }
        
        # Add user_id if request has authentication
        if hasattr(request.state, 'user_id'):
            key_data["user_id"] = request.state.user_id
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _should_cache(self, request: Request) -> bool:
        """
        Check if request should be cached
        :param request: FastAPI Request object
        :return: True if request should be cached, False otherwise
        """
        # Only cache GET requests
        if request.method not in self.cacheable_methods:
            return False
        
        # Don't cache if there are patterns to exclude
        request_path = request.url.path.lower()
        for pattern in self.no_cache_patterns:
            if pattern in request_path:
                return False
        
        # Don't cache if there is a Cache-Control: no-cache header
        if request.headers.get("cache-control") == "no-cache":
            return False
            
        return True

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get data from cache if it's valid
        :param cache_key: Cache key
        :return: Cache entry if it's valid, None otherwise
        """
        if cache_key not in self.cache:
            return None
        
        cache_entry = self.cache[cache_key]
        current_time = time.time()
        
        # Check if cache is expired
        if current_time > cache_entry["expires_at"]:
            # Expired - remove from cache
            del self.cache[cache_key]
            return None
        
        return cache_entry

    def _store_in_cache(self, cache_key: str, data: Dict[str, Any], ttl: int = None):
        """
        Store data in cache
        :param cache_key: Cache key
        :param data: Data to store
        :param ttl: Time to live
        """
        # Cleanup cache if it's full
        if len(self.cache) >= self.max_cache_size:
            # Remove 10% oldest entries
            sorted_keys = sorted(
                self.cache.keys(), 
                key=lambda k: self.cache[k]["created_at"]
            )
            for key in sorted_keys[:self.max_cache_size // 10]:
                del self.cache[key]
        
        ttl = ttl or self.default_ttl
        current_time = time.time()
        
        self.cache[cache_key] = {
            "data": data,
            "created_at": current_time,
            "expires_at": current_time + ttl,
            "ttl": ttl
        }

    async def handle(self, request: Request, credentials: HTTPAuthorizationCredentials = None):
        """
        Handle caching logic
        """
        # Only handle requests that can be cached
        if not self._should_cache(request):
            request.state.cache_status = "bypass"
            return {"cache": "bypass"}
        
        cache_key = self._generate_cache_key(request)
        
        # Try to get from cache
        cached_data = self._get_from_cache(cache_key)
        
        if cached_data:
            # Cache hit - return cached data
            request.state.cache_status = "hit"
            request.state.cache_key = cache_key
            request.state.cached_data = cached_data["data"]
            request.state.cache_ttl = cached_data["ttl"]
            request.state.cache_age = time.time() - cached_data["created_at"]
            
            return {
                "cache": "hit",
                "cache_key": cache_key[:8],  # Show first 8 characters of cache key
                "age": int(request.state.cache_age)
            }
        else:
            # Cache miss - will need to store response later
            request.state.cache_status = "miss"
            request.state.cache_key = cache_key
            
            # This middleware will need to be called again after the response to store the cache
            # Or can be implemented in response middleware/event
            
            return {
                "cache": "miss",
                "cache_key": cache_key[:8]
            }
    
    def store_response_in_cache(self, request: Request, response_data: Dict[str, Any], status_code: int):
        """
        Method to store response in cache (called from controller or response middleware)
        :param request: FastAPI Request object
        :param response_data: Response data to store
        :param status_code: HTTP status code
        """
        if (hasattr(request.state, 'cache_status') and 
            request.state.cache_status == "miss" and
            status_code in self.cacheable_status_codes):
            
            cache_key = request.state.cache_key
            
            # Calculate TTL based on response or use default
            ttl = self.default_ttl
            
            # Custom TTL based on endpoint
            if "/users/" in request.url.path:
                ttl = 600  # 10 minutes cho user data
            elif "/posts/" in request.url.path:
                ttl = 1800  # 30 minutes cho posts
            
            self._store_in_cache(cache_key, response_data, ttl)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        """
        return {
            "total_entries": len(self.cache),
            "max_size": self.max_cache_size,
            "usage_percent": (len(self.cache) / self.max_cache_size) * 100
        } 