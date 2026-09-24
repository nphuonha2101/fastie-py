<%!
import re

def to_class_name(name):
    return ''.join(word.capitalize() for word in to_snake_case(name).split('_'))

def to_snake_case(name):
    value = str(name).replace('-', '_').replace(' ', '_')
    value = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', value)
    value = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', value)
    return re.sub(r'_+', '_', value).strip('_').lower()

def unique_imports(fields):
    imports = {
        'from datetime import datetime',
        'from fastapi import APIRouter, Depends, HTTPException, Response, status',
        'from fastie.infrastructures.database.dependencies import get_db',
        'from sqlalchemy.exc import IntegrityError',
        'from sqlalchemy.orm import Session',
    }
    return '\n'.join(sorted(imports))
%>
<%
request_schema_root = "app.schemas.requests" if not schema_version else f"app.schemas.requests.{schema_version}"
response_schema_root = "app.schemas.responses" if not schema_version else f"app.schemas.responses.{schema_version}"
model_module = to_snake_case(model_name or name)
model_class_name = to_class_name(model_name or name)
%>
${unique_imports(fields)}
from app.models.${model_module} import ${model_class_name}
from ${request_schema_root}.${to_snake_case(name)}.${to_snake_case(name)}_create_schema import ${to_class_name(name)}CreateSchema
from ${request_schema_root}.${to_snake_case(name)}.${to_snake_case(name)}_update_schema import ${to_class_name(name)}UpdateSchema
from ${response_schema_root}.${to_snake_case(name)}.${to_snake_case(name)}_response_schema import ${to_class_name(name)}ResponseSchema


router = APIRouter()


def _get_or_404(item_id: int, db: Session) -> ${model_class_name}:
    item = (
        db.query(${model_class_name})
        .filter(
            ${model_class_name}.id == item_id,
            ${model_class_name}.deleted_at.is_(None),
        )
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="${to_class_name(name)} not found")
    return item


@router.get("/", response_model=list[${to_class_name(name)}ResponseSchema])
def index(db: Session = Depends(get_db)):
    return (
        db.query(${model_class_name})
        .filter(${model_class_name}.deleted_at.is_(None))
        .order_by(${model_class_name}.id)
        .all()
    )


@router.post("/", response_model=${to_class_name(name)}ResponseSchema, status_code=status.HTTP_201_CREATED)
def create(payload: ${to_class_name(name)}CreateSchema, db: Session = Depends(get_db)):
    item = ${model_class_name}(**payload.model_dump(exclude_unset=True))
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="${to_class_name(name)} conflicts with existing data") from exc
    db.refresh(item)
    return item


@router.get("/{item_id}", response_model=${to_class_name(name)}ResponseSchema)
def show(item_id: int, db: Session = Depends(get_db)):
    return _get_or_404(item_id, db)


@router.patch("/{item_id}", response_model=${to_class_name(name)}ResponseSchema)
def update(item_id: int, payload: ${to_class_name(name)}UpdateSchema, db: Session = Depends(get_db)):
    item = _get_or_404(item_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="${to_class_name(name)} conflicts with existing data") from exc
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def destroy(item_id: int, db: Session = Depends(get_db)):
    item = _get_or_404(item_id, db)
    item.deleted_at = datetime.utcnow()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
