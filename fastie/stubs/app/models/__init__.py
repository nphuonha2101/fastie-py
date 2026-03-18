# Import all models để Alembic có thể auto-detect schema changes
from .abstract_model import AbstractModel
from .user import User

__all__ = ['AbstractModel', 'User']
