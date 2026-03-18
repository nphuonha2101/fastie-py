<%!
def to_class_name(name):
    parts = name.lower().replace('-', '_').split('_')
    return ''.join(word.capitalize() for word in parts)

def to_snake_case(name):
    return name.lower().replace('-', '_')
%>\
from abc import ABC
from typing import Optional, List, Any
from fastie.core.decorators.di import repository
from fastie.repositories.implements.repository import Repository
from app.repositories.interfaces.${to_snake_case(name)}.i_${to_snake_case(name)}_repository import I${to_class_name(name)}Repository
# from app.models.${to_snake_case(name)} import ${to_class_name(name)}  # Uncomment when model exists

@repository
class ${to_class_name(name)}Repository(Repository, I${to_class_name(name)}Repository):
    def __init__(self):
        # Update with actual model class
        super().__init__(None)  # Replace None with model class 