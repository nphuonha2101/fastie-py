from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from fastie.core.paths.resource import __resources_path__
from fastie.core.providers.app_service_providers import initialize_application
from app.routes.api import register_routes

import app.api.v1.middlewares

load_dotenv()
initialize_application()
app = FastAPI()

app.mount("/static", StaticFiles(directory=f"{__resources_path__()}/public"), name="static")
register_routes(app)