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
from datetime import datetime, date
from pydantic import BaseModel, Field, EmailStr, HttpUrl, constr, conint, confloat, validator
from typing import Optional, List, Dict, Any, Union
from uuid import UUID

class ${to_class_name(name)}RequestSchema(BaseModel):
    """
    Request schema for ${to_title_case(name)}
    
    This schema defines the validation rules and constraints for
    incoming ${to_snake_case(name)} data in API requests.
    """
    # Request fields with validation
    # Examples:
    # name: str = Field(
    #     ...,  # Required field
    #     min_length=2,
    #     max_length=100,
    #     description="Name of the ${to_snake_case(name)}",
    #     example="Example ${to_title_case(name)}"
    # )
    # email: EmailStr = Field(
    #     ...,
    #     description="Email address",
    #     example="user@example.com"
    # )
    # age: Optional[conint(ge=0, le=150)] = Field(
    #     None,
    #     description="Age in years",
    #     example=25
    # )
    # tags: List[str] = Field(
    #     default_factory=list,
    #     description="List of tags",
    #     example=["tag1", "tag2"]
    # )
    
    # Custom validators example:
    # @validator('name')
    # def validate_name(cls, v):
    #     if len(v.strip()) == 0:
    #         raise ValueError('Name cannot be empty')
    #     return v.strip()
    
    # @validator('tags')
    # def validate_tags(cls, v):
    #     if len(v) > 10:
    #         raise ValueError('Maximum 10 tags allowed')
    #     return [tag.lower() for tag in v]
    
    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                # Add example values here matching your fields
                # "name": "Example ${to_title_case(name)}",
                # "email": "user@example.com",
                # "age": 25,
                # "tags": ["tag1", "tag2"]
            }
        }
        # Additional validation settings
        min_anystr_length = 1
        max_anystr_length = 1000
        str_strip_whitespace = True
        arbitrary_types_allowed = True 