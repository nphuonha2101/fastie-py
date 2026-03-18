import json
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from fastie.middlewares.abstract_middleware import AbstractMiddleware
from fastie.core.decorators.di import component


@component
class ValidationMiddleware(AbstractMiddleware):
    def __init__(self):
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        self.allowed_content_types = [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain"
        ]
        self.required_headers = ["user-agent"]  # Required headers

    async def handle(self, request: Request, credentials: HTTPAuthorizationCredentials = None):
        """
        Validate request before processing
        """
        # 1. Check request size
        content_length = request.headers.get("content-length")
        if content_length:
            content_length = int(content_length)
            if content_length > self.max_request_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Request quá lớn. Tối đa {self.max_request_size // (1024*1024)}MB",
                    headers={"X-Max-Size": str(self.max_request_size)}
                )
        
        # 2. Check Content-Type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            if content_type and content_type not in self.allowed_content_types:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Content-Type '{content_type}' không được hỗ trợ",
                    headers={
                        "X-Allowed-Content-Types": ", ".join(self.allowed_content_types)
                    }
                )
        
        # 3. Check required headers
        missing_headers = []
        for header in self.required_headers:
            if header not in request.headers:
                missing_headers.append(header)
        
        if missing_headers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required headers: {', '.join(missing_headers)}",
                headers={"X-Required-Headers": ", ".join(self.required_headers)}
            )
        
        # 4. Validate JSON structure cho JSON requests
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                # Only read a part to check JSON validity (not read the whole body)
                if hasattr(request, '_body'):
                    body = request._body
                    if body:
                        json.loads(body)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request body không phải JSON hợp lệ"
                )
        
        # 5. Check suspicious patterns (basic security)
        suspicious_patterns = ["<script", "javascript:", "eval(", "document.cookie"]
        request_data = str(request.url) + str(request.headers)
        
        for pattern in suspicious_patterns:
            if pattern.lower() in request_data.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request chứa nội dung không hợp lệ",
                    headers={"X-Security-Check": "failed"}
                )
        
        # Save validation info
        request.state.validation_passed = True
        request.state.request_size = content_length or 0
        request.state.content_type = request.headers.get("content-type", "unknown")
        
        return {
            "validation": "passed",
            "request_size": content_length or 0,
            "content_type": request.headers.get("content-type", "unknown")
        } 