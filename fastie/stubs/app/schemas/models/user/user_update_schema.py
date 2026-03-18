from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict


class UserUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[int] = None
    avatar: Optional[str] = None
    token: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)