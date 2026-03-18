<%!
def to_class_name(name):
    parts = name.lower().replace('-', '_').split('_')
    return ''.join(word.capitalize() for word in parts)

def to_title_case(name):
    return name.replace('_', ' ').replace('-', ' ').title()
%>\
from fastie.repositories.interfaces.i_repository import IRepository

class I${to_class_name(name)}Repository(IRepository):
    """Interface for ${to_title_case(name)} repository"""
    pass 