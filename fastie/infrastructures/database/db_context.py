from fastie.core.decorators.di import inject
from fastie.core.service_containers.service_containers import get_registry
from fastie.infrastructures.database.database_infrastructure import DatabaseInfrastructure

registry = get_registry()

@inject
class DbContext:
    """Compatibility unit-of-work wrapper; new routes should use ``get_db``."""

    def __init__(self, database: DatabaseInfrastructure):
        self.database = database
        self.session = None

    def __enter__(self):
        self.session = self.database.get_session()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type:
                self.session.rollback()
            else:
                try:
                    self.session.commit()
                except Exception:
                    self.session.rollback()
                    raise
        finally:
            self.session.close()

        return False
