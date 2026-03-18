<%!
def to_class_name(name):
    parts = name.lower().replace('-', '_').split('_')
    return ''.join(word.capitalize() for word in parts)

def to_snake_case(name):
    return name.lower().replace('-', '_')
%>\
from abc import ABC
from typing import Optional, List, Any
from fastie.core.decorators.di import service
from app.repositories.interfaces.${to_snake_case(name)}.i_${to_snake_case(name)}_repository import I${to_class_name(name)}Repository
from fastie.services.implements.service import Service
from app.services.interfaces.${to_snake_case(name)}.i_${to_snake_case(name)}_service import I${to_class_name(name)}Service

@service
class ${to_class_name(name)}Service(Service, I${to_class_name(name)}Service):
    def __init__(self, repository: I${to_class_name(name)}Repository):
        # Update with appropriate response schema
        super().__init__(repository, None)  # Replace None with response schema class 