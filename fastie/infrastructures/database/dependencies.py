"""FastAPI dependencies for database access.

The dependency is intentionally small: one request gets one SQLAlchemy
session, and the route owns its transaction boundary by calling commit or
rollback.  The older ``DbContext`` API remains available for compatibility.
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session

from fastie.infrastructures.database.database_infrastructure import DatabaseInfrastructure


@lru_cache(maxsize=1)
def get_database() -> DatabaseInfrastructure:
    """Return the process-local database infrastructure singleton."""
    return DatabaseInfrastructure()


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped database session for ``Depends(get_db)``."""
    db = get_database().get_session()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
