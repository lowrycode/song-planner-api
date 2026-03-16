import pytest
import os
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.dependencies import get_cron_allowed_church_activity_ids
from unittest.mock import patch


load_dotenv()
TEST_DB_URL = os.getenv("TEST_DB_URL")

engine = create_engine(TEST_DB_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Disable caching during tests
@pytest.fixture(autouse=True)
def disable_redis():
    with patch("app.utils.cache.redis_client", None):
        yield


# Create tables once before the test session
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# Provide a fresh database session for each test inside a transaction
# that is rolled back
@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# Override FastAPI dependency to use the test db session fixture
@pytest.fixture(scope="function")
def client(db_session):
    def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)


# Override get_cron_allowed_church_activity_ids
@pytest.fixture
def allow_cron_activities():
    def _override(activity_ids):
        app.dependency_overrides[get_cron_allowed_church_activity_ids] = (
            lambda: activity_ids
        )

    yield _override
    app.dependency_overrides.pop(get_cron_allowed_church_activity_ids, None)
