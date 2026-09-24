# Import all models for Alembic auto-detection of schema changes
from fastie.models.abstract_model import AbstractModel
from .refresh_token import RefreshToken
from .user import User

__all__ = ['AbstractModel', 'RefreshToken', 'User']
