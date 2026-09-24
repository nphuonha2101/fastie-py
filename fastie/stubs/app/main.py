import logging
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.staticfiles import StaticFiles

from fastie.infrastructures.database.dependencies import get_db
from fastie.core.config.config import get_config
from fastie.core.paths.resource import __resources_path__
from app.routes.api import register_routes

load_dotenv()
environment = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower()
get_config()
if environment in {"prod", "production"} and not os.getenv("REDIS_URL"):
    raise RuntimeError("REDIS_URL must be configured in production for shared auth rate limiting")
app = FastAPI()

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
allow_all_origins = "*" in allowed_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


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
