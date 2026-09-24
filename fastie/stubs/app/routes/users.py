"""User registration and account routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastie.core.securities.password import __hash_password__
from fastie.infrastructures.database.dependencies import get_db
from app.models.user import User
from app.routes.auth import _success, auth_rate_limit_with_headers, get_current_user
from app.schemas.models.user.user_create_schema import UserCreateSchema
from app.schemas.responses.user.user_response_schema import UserResponseSchema


user_router = APIRouter(prefix="/user", tags=["User"])


@user_router.post(
    "/register",
    summary="Register User",
    status_code=201,
    dependencies=[Depends(auth_rate_limit_with_headers)],
)
def register_user(request: UserCreateSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == request.email).first() is not None:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(
        **request.model_dump(exclude_unset=True, exclude={"password"}),
        password=__hash_password__(request.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered") from exc
    db.refresh(user)

    return _success(
        data=UserResponseSchema.model_validate(user),
        message="User registered successfully",
        status_code=201,
    )


@user_router.get("/", summary="Get All Users")
def list_users(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    users = (
        db.query(User)
        .filter(User.is_active.is_(True), User.deleted_at.is_(None))
        .order_by(User.id)
        .all()
    )
    return _success(
        data=[UserResponseSchema.model_validate(user) for user in users],
        message="Users retrieved successfully",
    )
