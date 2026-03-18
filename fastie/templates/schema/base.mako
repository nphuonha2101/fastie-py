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
from pydantic import BaseModel, ConfigDict, Field, EmailStr, HttpUrl, constr, conint, confloat
from typing import Optional, List, Dict, Any, Union
from uuid import UUID

class ${to_class_name(name)}BaseSchema(BaseModel):
    """
    Base schema for ${to_title_case(name)}
    
    This schema defines the base fields and validation rules for ${to_snake_case(name)} data.
    It is used as a foundation for request and response schemas.
    """
    # Common fields with validation
    # Examples:
    # id: Optional[int] = Field(None, description="Unique identifier")
    # uuid: Optional[UUID] = Field(None, description="UUID identifier")
    # name: str = Field(..., min_length=2, max_length=100, description="Name of the ${to_snake_case(name)}")
    # email: Optional[EmailStr] = Field(None, description="Email address")
    # age: Optional[conint(ge=0, le=150)] = Field(None, description="Age in years")
    # price: Optional[confloat(ge=0)] = Field(None, description="Price amount")
    # url: Optional[HttpUrl] = Field(None, description="Website URL")
    # phone: Optional[constr(regex=r'^\+?1?\d{9,15}$')] = Field(None, description="Phone number")
    # tags: List[str] = Field(default_factory=list, description="List of tags")
    # metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    # created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    # updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    # is_active: bool = Field(True, description="Whether the ${to_snake_case(name)} is active")
    
    model_config = ConfigDict(
        from_attributes=True,  # Allow ORM model attribute access
        json_schema_extra={
            "example": {
                # Add example values here
                # "name": "Example ${to_title_case(name)}",
                # "email": "example@domain.com",
                # "is_active": True
            }
        }
    ) 