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
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, EmailStr, HttpUrl, computed_field
from typing import Optional, List, Dict, Any, Union
from uuid import UUID

class ${to_class_name(name)}ResponseSchema(BaseModel):
    """
    Response schema for ${to_title_case(name)}
    
    This schema defines the structure and format of ${to_snake_case(name)} data
    returned in API responses.
    """
    # Required base fields
    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Optional common fields
    # uuid: UUID = Field(..., description="UUID identifier")
    # name: str = Field(..., description="Name of the ${to_snake_case(name)}")
    # description: Optional[str] = Field(None, description="Description")
    # email: Optional[EmailStr] = Field(None, description="Email address")
    # url: Optional[HttpUrl] = Field(None, description="Website URL")
    # metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    # tags: List[str] = Field(default_factory=list, description="Associated tags")
    # is_active: bool = Field(True, description="Active status")
    
    # Computed fields example:
    # @computed_field
    # @property
    # def display_name(self) -> str:
    #     """Generate a display name"""
    #     return f"{self.name} ({self.id})"
    
    # @computed_field
    # @property
    # def age_days(self) -> Optional[int]:
    #     """Calculate age in days"""
    #     if self.created_at:
    #         return (datetime.utcnow() - self.created_at).days
    #     return None
    
    model_config = ConfigDict(
        from_attributes=True,  # Allow ORM model attribute access
        json_schema_extra={
            "example": {
                "id": 1,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-02T00:00:00",
                # Add more example values here
                # "name": "Example ${to_title_case(name)}",
                # "description": "A detailed description",
                # "is_active": True
            }
        }
    )
    
    class Config:
        """Additional configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        } 