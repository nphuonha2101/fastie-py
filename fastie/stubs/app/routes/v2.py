"""Version 2 API router.

Add only endpoints whose response or request contract is intentionally
different from v1. Existing v1 endpoints remain available during migration.
"""

from fastapi import APIRouter


v2_router = APIRouter(prefix="/v2")

# Fastie resource routes - generated imports

# Fastie resource routes - generated includes
