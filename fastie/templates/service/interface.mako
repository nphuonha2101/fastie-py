<%!
def to_class_name(name):
    parts = name.lower().replace('-', '_').split('_')
    return ''.join(word.capitalize() for word in parts)

def to_title_case(name):
    return name.replace('_', ' ').replace('-', ' ').title()
%>\
from fastie.services.interfaces.i_service import IService

class I${to_class_name(name)}Service(IService):
    """Interface for ${to_title_case(name)} service"""
    pass 