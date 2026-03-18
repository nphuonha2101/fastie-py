<%!
def to_class_name(name):
    """Convert name to proper PascalCase class name"""
    parts = name.lower().replace('-', '_').split('_')
    return ''.join(word.capitalize() for word in parts)

def to_snake_case(name):
    """Convert name to snake_case"""
    return name.lower().replace('-', '_')

def to_title_case(name):
    """Convert name to Title Case"""
    return name.replace('_', ' ').replace('-', ' ').title()
%>\
from abc import ABC
from fastie.controllers.base_controller import BaseController
from fastie.core.decorators.di import controller, inject
from app.services.interfaces.${to_snake_case(name)}.i_${to_snake_case(name)}_service import I${to_class_name(name)}Service

@controller
@inject
class ${to_class_name(name)}Controller(BaseController, ABC):
    def __init__(self, ${to_snake_case(name)}_service: I${to_class_name(name)}Service):
        super().__init__()
        self.${to_snake_case(name)}_service = ${to_snake_case(name)}_service

    def define_routes(self):
        """Define all routes for this controller"""
        self.router.get("/", summary="Get ${to_title_case(name)}", status_code=200)(self.index)

    def index(self):
        """Handle ${to_snake_case(name)} requests"""
        try:
            return self.success(message="${to_title_case(name)} endpoint working!")
        except Exception as e:
            return self.error(message=str(e)) 