from abc import abstractmethod, ABC
import logging

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

from fastie.core.service_containers.service_containers import get_registry


class BaseController(ABC):
    def __init__(self):
        self.router = APIRouter()
        self.registry = get_registry()
        self.logger = logging.getLogger(self.__class__.__name__)

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

    def internal_error(self, exception: Exception):
        """Log the exception while returning a safe public error message."""
        self.logger.error(
            "Unhandled controller exception",
            exc_info=(type(exception), exception, exception.__traceback__),
        )
        return self.error(message="Internal server error", status_code=500)
