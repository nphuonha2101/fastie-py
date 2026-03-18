from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional


class UserBaseSchema(BaseModel):
    name: str
    email: EmailStr
    is_active: bool = True
    avatar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)