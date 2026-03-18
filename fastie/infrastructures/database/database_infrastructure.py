from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import logging

from fastie.core.decorators.di import infrastructure

logger = logging.getLogger(__name__)
Base = declarative_base()

@infrastructure
class DatabaseInfrastructure:
    def __init__(self):
        try:
            self.database_url = os.getenv("DATABASE_URL")
            if not self.database_url:
                raise ValueError("DATABASE_URL is not set in .env")

            # Special handling for SQLite
            engine_args = {"pool_pre_ping": True}
            if self.database_url.startswith("sqlite"):
                engine_args["connect_args"] = {"check_same_thread": False}

            self.engine = create_engine(self.database_url, **engine_args)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info(f"Database engine created successfully for {self.database_url.split(':', 1)[0]}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def get_session(self):
        try:
            db = self.SessionLocal()
            return db
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
