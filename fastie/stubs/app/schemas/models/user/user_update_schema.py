from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict, Field


class UserUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8)
    is_active: Optional[bool] = None
    avatar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
