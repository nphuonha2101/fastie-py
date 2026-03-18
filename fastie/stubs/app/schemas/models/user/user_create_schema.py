from app.schemas.models.user.user_base_schema import UserBaseSchema


class UserCreateSchema(UserBaseSchema):
    password: str