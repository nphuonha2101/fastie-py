from abc import abstractmethod, ABC

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

from fastie.core.service_containers.service_containers import get_registry


class BaseController(ABC):
    def __init__(self):
        self.router = APIRouter()
        self.registry = get_registry()

    @abstractmethod
    def define_routes(self):
        """
        This method should be overridden in subclasses to define specific routes.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def success(self, content=None, message="Success", status_code=200):
        """
        Defines base API response structures for success messages.
        :param content: Optional data to include in the response.
        :param message: Optional message to include in the response.
        :param status_code: HTTP status code for the response, default is 200.
        """
        content = {
                "status_code": status_code,
                "success": True,
                "status": "success",
                "message": message,
                "data": jsonable_encoder(content)
            }

        return JSONResponse(status_code=status_code, content=content)

    def error(self, message="Error", status_code=400):
        """
        Defines base API response structures for error messages.
        :param message: Optional error message to include in the response.
        :param status_code: HTTP status code for the response, default is 400.
        """
        content = {
            "status_code": status_code,
            "success": False,
            "status": "error",
            "message": message,
            "data": None
        }
        return JSONResponse(status_code=status_code, content=content)