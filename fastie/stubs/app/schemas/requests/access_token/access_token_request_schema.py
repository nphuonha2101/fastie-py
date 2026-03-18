from pydantic import BaseModel


class AccessTokenRequestSchema(BaseModel):
    email: str
    password: str
