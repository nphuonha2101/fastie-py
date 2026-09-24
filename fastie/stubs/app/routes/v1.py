"""Version 1 API router.

Keep this router stable for existing clients. New breaking contracts should
be introduced in a separate version module instead of changing v1 in place.
"""

from fastapi import APIRouter

from app.routes.auth import auth_router
from app.routes.users import user_router


v1_router = APIRouter(prefix="/v1")
v1_router.include_router(auth_router)
v1_router.include_router(user_router)

# Fastie resource routes - generated imports

# Fastie resource routes - generated includes
