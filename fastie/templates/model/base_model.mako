<%!
def to_class_name(name):
    """Convert name to proper PascalCase class name"""
    parts = name.lower().replace('-', '_').split('_')
    return ''.join(word.capitalize() for word in parts)

def to_snake_case(name):
    """Convert name to snake_case"""
    return name.lower().replace('-', '_')

def get_table_name(name):
    """Generate table name from model name"""
    return f"{to_snake_case(name)}s"

def generate_field_definition(field_spec):
    """Generate SQLAlchemy field definition with proper type and constraints"""
    parts = field_spec.split(':')
    field_name = to_snake_case(parts[0].strip())
    field_type = parts[1].strip().lower()
    field_params = parts[2:] if len(parts) > 2 else []
    
    type_map = {
        'str': ('String', '255', 'nullable=False'),
        'string': ('String', '255', 'nullable=False'),
        'text': ('Text', None, 'nullable=True'),
        'int': ('Integer', None, 'nullable=False'),
        'integer': ('Integer', None, 'nullable=False'),
        'bool': ('Boolean', None, 'default=True'),
        'boolean': ('Boolean', None, 'default=True'),
        'datetime': ('DateTime', None, 'default=datetime.utcnow'),
        'date': ('Date', None, 'nullable=True'),
        'float': ('Float', None, 'nullable=False'),
        'decimal': ('Decimal', '10,2', 'nullable=False'),
        'json': ('JSON', None, 'nullable=True'),
        'uuid': ('UUID', None, 'nullable=False'),
        'email': ('String', '255', 'nullable=False, index=True'),
        'url': ('String', '2048', 'nullable=True'),
        'phone': ('String', '20', 'nullable=True'),
    }
    
    if field_type in type_map:
        sql_type, default_size, constraints = type_map[field_type]
        
        # Handle size parameter if provided
        if field_params and sql_type in ['String', 'Decimal']:
            if sql_type == 'Decimal':
                precision, scale = field_params[0].split(',') if ',' in field_params[0] else (field_params[0], '2')
                return f"    {field_name} = Column({sql_type}({precision},{scale}), {constraints})"
            else:
                return f"    {field_name} = Column({sql_type}({field_params[0]}), {constraints})"
        
        # Use default size if applicable
        if default_size:
            return f"    {field_name} = Column({sql_type}({default_size}), {constraints})"
        return f"    {field_name} = Column({sql_type}, {constraints})"
    
    # Default to string if type is unknown
    return f"    {field_name} = Column(String(255), nullable=False)  # Unknown type: {field_type}"
%>\
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Date, Float, JSON, UUID
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.types import DECIMAL as Decimal
from fastie.models.abstract_model import AbstractModel
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, date

class ${to_class_name(name)}(AbstractModel):
    """
    ${to_class_name(name)} model
    
    Represents a ${to_snake_case(name)} entity in the system.
    Table name: ${get_table_name(name)}
    """
    __tablename__ = '${get_table_name(name)}'
    
    def get_response_model(self) -> Optional[BaseModel]:
        """Get the Pydantic model for API responses"""
        # TODO: Update with actual response schema when available
        return None

% if fields:
    # Model fields
% for field in fields.split(','):
${generate_field_definition(field)}
% endfor
% else:
    # Add your model fields here
    # Examples:
    # name = Column(String(100), nullable=False)
    # description = Column(Text, nullable=True)
    # price = Column(Decimal(10,2), nullable=False)
    # created_at = Column(DateTime, default=datetime.utcnow)
    # is_active = Column(Boolean, default=True)
% endif

    def __repr__(self) -> str:
        """String representation of the model"""
        fields = []
        if hasattr(self, 'id'):
            fields.append(f"id={self.id}")
        if hasattr(self, 'name'):
            fields.append(f"name='{self.name}'")
        if hasattr(self, 'sku'):
            fields.append(f"sku='{self.sku}'")
        if hasattr(self, 'is_active'):
            fields.append(f"active={self.is_active}")
        return f"<{to_class_name(name)}({', '.join(fields)})>" 