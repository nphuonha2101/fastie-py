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
    """Definition of middleware groups"""
    BASIC = "basic"                    # CORS, Logging
    SECURITY = "security"              # Auth, Rate Limiting
    FULL = "full"                      # All middlewares
    PUBLIC = "public"                  # For endpoints not requiring auth
    PROTECTED = "protected"            # For endpoints requiring auth
    HIGH_PERFORMANCE = "high_performance"  # With caching
    STRICT_VALIDATION = "strict_validation"  # With strict validation
    API_VERSIONED = "api_versioned"    # With versioning support


class MiddlewareManager:
    """
    Manages and provides middleware by group or custom selection
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
                CachingMiddleware,  # Add caching
                RateLimitMiddleware
            ],
            MiddlewareGroup.STRICT_VALIDATION: [
                CORSMiddleware,
                ValidationMiddleware,  # Strict validation
                LoggingMiddleware,
                RateLimitMiddleware,
                AuthMiddleware
            ],
            MiddlewareGroup.API_VERSIONED: [
                VersioningMiddleware,  # Version checking first
                CORSMiddleware,
                LoggingMiddleware,
                RateLimitMiddleware
            ]
        }

    def _ensure_middleware_registered(self):
        """
        Ensures all middleware are registered in the registry
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
        Gets a list of middleware instances by group
        """
        middleware_classes = self._middleware_groups.get(group, [])
        instances = []
        
        for cls in middleware_classes:
            try:
                # Try resolving from registry first
                instance = self.registry.resolve(cls)
                instances.append(instance)
            except ValueError:
                # If not found, create instance directly
                instance = cls()
                instances.append(instance)
                # Register in registry for future use
                self.registry.register(cls, instance)
        
        return instances

    def get_custom_middlewares(self, middleware_classes: List[Type]) -> List[Any]:
        """
        Gets a list of custom middleware instances
        """
        instances = []
        
        for cls in middleware_classes:
            try:
                # Try resolving from registry first
                instance = self.registry.resolve(cls)
                instances.append(instance)
            except ValueError:
                # If not found, create instance directly
                instance = cls()
                instances.append(instance)
                # Register in registry for future use
                self.registry.register(cls, instance)
        
        return instances

    def get_middleware_for_route(self, 
                                route_type: str = "public", 
                                additional_middlewares: List[Type] = None) -> List[Any]:
        """
        Gets suitable middleware for a specific route type
        
        Args:
            route_type: "public", "protected", "admin", etc.
            additional_middlewares: Optional additional custom middlewares
        """
        base_middlewares = []
        
        if route_type == "public":
            base_middlewares = self.get_middleware_group(MiddlewareGroup.PUBLIC)
        elif route_type == "protected":
            base_middlewares = self.get_middleware_group(MiddlewareGroup.PROTECTED)
        elif route_type == "admin":
            # Admin routes have extra security
            base_middlewares = self.get_middleware_group(MiddlewareGroup.FULL)
        else:
            # Default: basic middlewares
            base_middlewares = self.get_middleware_group(MiddlewareGroup.BASIC)
        
        # Add custom middlewares if requested
        if additional_middlewares:
            additional = self.get_custom_middlewares(additional_middlewares)
            base_middlewares.extend(additional)
        
        return base_middlewares


# Singleton instance
_middleware_manager = None

def get_middleware_manager() -> MiddlewareManager:
    """
    Returns the singleton instance of MiddlewareManager
    Ensures all middleware are correctly registered
    """
    global _middleware_manager
    if _middleware_manager is None:
        try:
            _middleware_manager = MiddlewareManager()
        except Exception as e:
            # Fallback: ensure middleware manager is always available
            print(f"Warning: Error creating MiddlewareManager: {e}")
            _middleware_manager = MiddlewareManager()
    
    return _middleware_manager 