import os
from collections.abc import Generator

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret-123456789012345678901234")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ISSUER", "fastie-test")
os.environ.setdefault("JWT_AUDIENCE", "fastie-test-api")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("ALLOWED_HOSTS", "*")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://testserver")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register all generated models with metadata
from app.main import app
from fastie.infrastructures.database.database_infrastructure import Base
from fastie.infrastructures.database.dependencies import get_db


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)


@pytest.fixture(autouse=True)
def database() -> Generator[Session, None, None]:
    """Provide a clean in-memory database for every test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def override_database(database: Session) -> Generator[None, None, None]:
    """Replace the production database dependency with the test session."""
    def override_get_db() -> Generator[Session, None, None]:
        yield database

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
