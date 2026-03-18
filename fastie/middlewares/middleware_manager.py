from typing import List, Type, Dict, Any
from enum import Enum

from fastie.core.service_containers.service_containers import get_registry

# Force import all middleware to trigger @component decorators
from fastie.middlewares.auth.auth_middleware import AuthMiddleware
from fastie.middlewares.cors_middleware import CORSMiddleware
from fastie.middlewares.logging_middleware import LoggingMiddleware
from fastie.middlewares.rate_limit_middleware import RateLimitMiddleware
from fastie.middlewares.versioning_middleware import VersioningMiddleware
from fastie.middlewares.validation_middleware import ValidationMiddleware
from fastie.middlewares.caching_middleware import CachingMiddleware

# Ensure all middleware classes are imported to trigger @component decorator
_MIDDLEWARE_CLASSES = [
    AuthMiddleware,
    CORSMiddleware, 
    LoggingMiddleware,
    RateLimitMiddleware,
    VersioningMiddleware,
    ValidationMiddleware,
    CachingMiddleware
]


class MiddlewareGroup(Enum):
    """Định nghĩa các nhóm middleware"""
    BASIC = "basic"                    # CORS, Logging
    SECURITY = "security"              # Auth, Rate Limiting
    FULL = "full"                      # Tất cả middleware
    PUBLIC = "public"                  # Cho endpoints không cần auth
    PROTECTED = "protected"            # Cho endpoints cần auth
    HIGH_PERFORMANCE = "high_performance"  # Với caching
    STRICT_VALIDATION = "strict_validation"  # Với validation nghiêm ngặt
    API_VERSIONED = "api_versioned"    # Với versioning support


class MiddlewareManager:
    """
    Quản lý và cung cấp middleware theo nhóm hoặc tùy chỉnh
    """
    
    def __init__(self):
        self.registry = get_registry()
        
        # Force register all middleware to ensure availability
        self._ensure_middleware_registered()
        
        self._middleware_groups = {
            MiddlewareGroup.BASIC: [
                CORSMiddleware,
                LoggingMiddleware
            ],
            MiddlewareGroup.SECURITY: [
                AuthMiddleware,
                RateLimitMiddleware
            ],
            MiddlewareGroup.PUBLIC: [
                CORSMiddleware,
                LoggingMiddleware,
                RateLimitMiddleware
            ],
            MiddlewareGroup.PROTECTED: [
                CORSMiddleware,
                LoggingMiddleware,
                RateLimitMiddleware,
                AuthMiddleware
            ],
            MiddlewareGroup.FULL: [
                CORSMiddleware,
                LoggingMiddleware,
                RateLimitMiddleware,
                AuthMiddleware
            ],
            MiddlewareGroup.HIGH_PERFORMANCE: [
                CORSMiddleware,
                LoggingMiddleware,
                CachingMiddleware,  # Thêm caching
                RateLimitMiddleware
            ],
            MiddlewareGroup.STRICT_VALIDATION: [
                CORSMiddleware,
                ValidationMiddleware,  # Validation nghiêm ngặt
                LoggingMiddleware,
                RateLimitMiddleware,
                AuthMiddleware
            ],
            MiddlewareGroup.API_VERSIONED: [
                VersioningMiddleware,  # Version checking đầu tiên
                CORSMiddleware,
                LoggingMiddleware,
                RateLimitMiddleware
            ]
        }

    def _ensure_middleware_registered(self):
        """
        Đảm bảo tất cả middleware đã được đăng ký vào registry
        """
        for middleware_cls in _MIDDLEWARE_CLASSES:
            # All middleware should be in the registry after load_components()
            # This call just ensures they are resolvable.
            try:
                self.registry.resolve(middleware_cls)
            except ValueError:
                # If for some reason not in registry, it will be handled when requested
                pass

    def get_middleware_group(self, group: MiddlewareGroup) -> List[Any]:
        """
        Lấy danh sách middleware instances theo nhóm
        """
        middleware_classes = self._middleware_groups.get(group, [])
        instances = []
        
        for cls in middleware_classes:
            try:
                # Thử resolve từ registry trước
                instance = self.registry.resolve(cls)
                instances.append(instance)
            except ValueError:
                # Nếu không tìm thấy, tạo instance trực tiếp
                instance = cls()
                instances.append(instance)
                # Đăng ký vào registry cho lần sau
                self.registry.register(cls, instance)
        
        return instances

    def get_custom_middlewares(self, middleware_classes: List[Type]) -> List[Any]:
        """
        Lấy danh sách middleware instances tùy chỉnh
        """
        instances = []
        
        for cls in middleware_classes:
            try:
                # Thử resolve từ registry trước
                instance = self.registry.resolve(cls)
                instances.append(instance)
            except ValueError:
                # Nếu không tìm thấy, tạo instance trực tiếp
                instance = cls()
                instances.append(instance)
                # Đăng ký vào registry cho lần sau
                self.registry.register(cls, instance)
        
        return instances

    def get_middleware_for_route(self, 
                                route_type: str = "public", 
                                additional_middlewares: List[Type] = None) -> List[Any]:
        """
        Lấy middleware phù hợp cho loại route cụ thể
        
        Args:
            route_type: "public", "protected", "admin", etc.
            additional_middlewares: Thêm middleware tùy chỉnh
        """
        base_middlewares = []
        
        if route_type == "public":
            base_middlewares = self.get_middleware_group(MiddlewareGroup.PUBLIC)
        elif route_type == "protected":
            base_middlewares = self.get_middleware_group(MiddlewareGroup.PROTECTED)
        elif route_type == "admin":
            # Admin routes có thêm security
            base_middlewares = self.get_middleware_group(MiddlewareGroup.FULL)
        else:
            # Default: basic middlewares
            base_middlewares = self.get_middleware_group(MiddlewareGroup.BASIC)
        
        # Thêm middleware tùy chỉnh nếu có
        if additional_middlewares:
            additional = self.get_custom_middlewares(additional_middlewares)
            base_middlewares.extend(additional)
        
        return base_middlewares


# Singleton instance
_middleware_manager = None

def get_middleware_manager() -> MiddlewareManager:
    """
    Lấy singleton instance của MiddlewareManager
    Đảm bảo tất cả middleware được đăng ký đúng cách
    """
    global _middleware_manager
    if _middleware_manager is None:
        try:
            _middleware_manager = MiddlewareManager()
        except Exception as e:
            # Fallback: đảm bảo middleware manager luôn khả dụng
            print(f"Warning: Error creating MiddlewareManager: {e}")
            _middleware_manager = MiddlewareManager()
    
    return _middleware_manager 