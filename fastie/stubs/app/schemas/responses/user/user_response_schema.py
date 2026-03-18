from pydantic import EmailStr, ConfigDict, BaseModel
from typing import Optional


class UserResponseSchema(BaseModel):
    """
    Schema for user response. Excludes sensitive fields.
    """
    id: int
    name: str
    email: EmailStr
    is_active: bool = True
    avatar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)