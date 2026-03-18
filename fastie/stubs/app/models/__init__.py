# Import all models for Alembic auto-detection of schema changes
from fastie.models.abstract_model import AbstractModel
from .user import User

__all__ = ['AbstractModel', 'User']
