import logging
import os
import re
from contextlib import asynccontextmanager
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.staticfiles import StaticFiles

from fastie.infrastructures.database.dependencies import get_db
from fastie.core.config.config import get_config
from fastie.core.paths.resource import __resources_path__
from app.routes.api import close_auth_rate_limiter, register_routes

load_dotenv()
environment = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower()
config = get_config()


def _csv_setting(name: str, default: str = "") -> list[str]:
    value = config.get(name, default)
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


allowed_hosts = _csv_setting("ALLOWED_HOSTS", "*")
allowed_origins = _csv_setting("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
allow_all_origins = "*" in allowed_origins


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_auth_rate_limiter()


app = FastAPI(lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", request_id):
        request_id = str(uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if environment in {"prod", "production"}:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    logger.info(
        "%s %s -> %s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        request_id,
    )
    return response


@app.get("/healthz", tags=["system"])
def healthz():
    return {"status": "ok"}


@app.get("/readyz", tags=["system"])
def readyz(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready",
        ) from exc
    return {"status": "ready"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled application exception",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={
            "status_code": 500,
            "success": False,
            "status": "error",
            "message": "Internal server error",
            "data": None,
        },
    )

app.mount("/static", StaticFiles(directory=f"{__resources_path__()}/public"), name="static")
register_routes(app)
