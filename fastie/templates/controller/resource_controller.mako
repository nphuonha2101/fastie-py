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
        self.router.get("/", summary="Get All ${to_title_case(name)}", status_code=200)(self.index)
        self.router.post("/", summary="Create ${to_title_case(name)}", status_code=201)(self.create)
        self.router.get("/{id}", summary="Get ${to_title_case(name)}", status_code=200)(self.show)
        self.router.put("/{id}", summary="Update ${to_title_case(name)}", status_code=200)(self.update)
        self.router.delete("/{id}", summary="Delete ${to_title_case(name)}", status_code=204)(self.delete)

    def index(self):
        """Get all ${to_snake_case(name)}s"""
        try:
            ${to_snake_case(name)}s = self.${to_snake_case(name)}_service.get_all()
            return self.success(content=${to_snake_case(name)}s, message="${to_title_case(name)}s retrieved successfully.")
        except Exception as e:
            return self.error(message=str(e))

    def create(self):
        """Create a new ${to_snake_case(name)}"""
        try:
            # Implementation needed
            return self.success(message="${to_title_case(name)} created successfully.")
        except Exception as e:
            return self.error(message=str(e))

    def show(self, id: int):
        """Get ${to_snake_case(name)} by ID"""
        try:
            ${to_snake_case(name)} = self.${to_snake_case(name)}_service.get_by_id(id)
            return self.success(content=${to_snake_case(name)}, message="${to_title_case(name)} retrieved successfully.")
        except Exception as e:
            return self.error(message=str(e))

    def update(self, id: int):
        """Update ${to_snake_case(name)}"""
        try:
            # Implementation needed
            return self.success(message="${to_title_case(name)} updated successfully.")
        except Exception as e:
            return self.error(message=str(e))

    def delete(self, id: int):
        """Delete ${to_snake_case(name)}"""
        try:
            self.${to_snake_case(name)}_service.delete(id)
            return self.success(message="${to_title_case(name)} deleted successfully.")
        except Exception as e:
            return self.error(message=str(e)) 