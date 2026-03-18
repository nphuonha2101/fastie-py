from fastie.core.decorators.di import inject
from fastie.core.service_containers.service_containers import get_registry
from fastie.infrastructures.database.database_infrastructure import DatabaseInfrastructure

registry = get_registry()

@inject
class DbContext:
    def __init__(self, database: DatabaseInfrastructure):
        self.database = database
        self.session = None

    def __enter__(self):
        self.session = self.database.get_session()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()

