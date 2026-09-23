import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from fastie.core.paths.resource import __resources_path__
from fastie.core.providers.app_service_providers import initialize_application
from app.routes.api import register_routes

import app.api.v1.middlewares

load_dotenv()
initialize_application()
app = FastAPI()

logger = logging.getLogger(__name__)


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
