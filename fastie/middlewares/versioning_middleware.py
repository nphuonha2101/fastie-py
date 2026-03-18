from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from fastie.middlewares.abstract_middleware import AbstractMiddleware
from fastie.core.decorators.di import component


@component
class VersioningMiddleware(AbstractMiddleware):
    def __init__(self):
        self.supported_versions = ["v1", "v2"]
        self.default_version = "v1"

    async def handle(self, request: Request, credentials: HTTPAuthorizationCredentials = None):
        """
        Check and handle API versioning
        """
        # Get version from header or URL
        api_version = None
        
        # Way 1: From header Accept-Version
        if "accept-version" in request.headers:
            api_version = request.headers["accept-version"]
        
        # Way 2: From URL path (already has /api/v1)
        elif "/api/" in str(request.url.path):
            path_parts = request.url.path.split("/")
            for part in path_parts:
                if part.startswith("v") and part[1:].isdigit():
                    api_version = part
                    break
        
        # Way 3: From query parameter
        elif "version" in request.query_params:
            version_param = request.query_params["version"]
            api_version = f"v{version_param}" if not version_param.startswith("v") else version_param
        
        # Use default version if not exists
        if not api_version:
            api_version = self.default_version
        
        # Validate version
        if api_version not in self.supported_versions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"API version '{api_version}' is not supported. Supported versions: {', '.join(self.supported_versions)}",
                headers={"X-Supported-Versions": ", ".join(self.supported_versions)}
            )
        
        # Save version info to request state
        request.state.api_version = api_version
        request.state.version_headers = {
            "X-API-Version": api_version,
            "X-Supported-Versions": ", ".join(self.supported_versions)
        }
        
        return {
            "api_version": api_version,
            "supported_versions": self.supported_versions
        } 