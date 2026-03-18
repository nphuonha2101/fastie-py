<%!
    # Helper functions for templates
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
%>

<%def name="standard_imports()">
from abc import ABC
from typing import Optional, List, Any
</%def>

<%def name="controller_imports()">
${standard_imports()}
from fastie.controllers.base_controller import BaseController
from fastie.core.decorators.di import controller, inject
</%def>

<%def name="service_imports()">
${standard_imports()}
from fastie.core.decorators.di import service
</%def>

<%def name="repository_imports()">
${standard_imports()}
from fastie.core.decorators.di import repository
</%def>

<%def name="model_imports()">
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from fastie.models.abstract_model import AbstractModel
from typing import Optional
from pydantic import BaseModel
</%def>

<%def name="schema_imports()">
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
</%def> 