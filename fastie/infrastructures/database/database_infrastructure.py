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

            self.engine = create_engine(self.database_url, pool_pre_ping=True)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("Database engine created successfully")

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
