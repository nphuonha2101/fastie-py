from fastapi import APIRouter, FastAPI, Depends
from typing import List, Type, Callable, Union

from fastie.middlewares.middleware_manager import get_middleware_manager, MiddlewareGroup
from fastie.core.service_containers.service_containers import get_registry


class RouteRegistrar:
    """
    A class to register API routes in a FastAPI application.
    This class allows for modular route registration by encapsulating the logic
    for registering controllers and their routes under a specified prefix.
    """
    def __init__(self, app: FastAPI, prefix: str = "/api/v1"):
        self.app = app
        self.api_router = APIRouter(prefix=prefix)
        self.registry = get_registry()
        self.middleware_manager = get_middleware_manager()

    def register(
            self,
            controller_class: Type,
            prefix: str = "",
            tags: List[str] = None,
            middleware: Union[List[Callable], MiddlewareGroup, str] = None,
            route_type: str = "public",
            additional_middlewares: List[Type] = None
    ):
        controller = self.registry.resolve(controller_class)
        if not controller or not hasattr(controller, 'router'):
            raise ValueError(f"Controller {controller_class.__name__} is not properly registered or does not have a router.")

        # Trigger route definition after injection is complete
        if hasattr(controller, 'define_routes'):
            controller.define_routes()

        # Handle middleware dynamically
        final_middlewares = []

        if middleware is not None:
            if isinstance(middleware, MiddlewareGroup):
                # Use middleware group
                final_middlewares = self.middleware_manager.get_middleware_group(middleware)
            elif isinstance(middleware, str):
                # Use route type
                final_middlewares = self.middleware_manager.get_middleware_for_route(
                    middleware, additional_middlewares
                )
            elif isinstance(middleware, list):
                # Middleware list passed directly (backward compatibility)
                final_middlewares = middleware
        else:
            # Use default route_type
            final_middlewares = self.middleware_manager.get_middleware_for_route(
                route_type, additional_middlewares
            )

        sub_router = APIRouter(
            prefix=prefix,
            tags=tags or [],
            dependencies=[Depends(m) for m in final_middlewares]
        )

        sub_router.include_router(controller.router)

        self.api_router.include_router(sub_router)

    def apply(self):
        self.app.include_router(self.api_router)