from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()

class DatabaseInfrastructure:
    def __init__(self):
        try:
            self.database_url = os.getenv("DATABASE_URL")
            if not self.database_url:
                raise ValueError("DATABASE_URL is not set in .env")

            engine_args = {"pool_pre_ping": True}
            if self.database_url.startswith("sqlite"):
                engine_args["connect_args"] = {"check_same_thread": False}
            else:
                engine_args.update(
                    pool_size=self._int_env("DB_POOL_SIZE", 5),
                    max_overflow=self._int_env("DB_MAX_OVERFLOW", 10),
                    pool_timeout=self._int_env("DB_POOL_TIMEOUT", 30),
                    pool_recycle=self._int_env("DB_POOL_RECYCLE", 1800),
                )

            if self._bool_env("DB_ECHO", False):
                engine_args["echo"] = True

            self.engine = create_engine(self.database_url, **engine_args)
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
                bind=self.engine,
            )
            logger.info(
                "Database engine created successfully for %s",
                self.database_url.split(":", 1)[0],
            )

        except Exception:
            logger.exception("Failed to initialize database")
            raise

    def get_session(self):
        try:
            db = self.SessionLocal()
            return db
        except Exception:
            logger.exception("Failed to create database session")
            raise

    @staticmethod
    def _int_env(name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None or value == "":
            return default
        parsed = int(value)
        if parsed <= 0:
            raise ValueError(f"{name} must be greater than zero")
        return parsed

    @staticmethod
    def _bool_env(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}
