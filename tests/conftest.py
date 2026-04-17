# tests/conftest.py
import os
import sys
from sqlmodel import SQLModel, create_engine
from sqlalchemy.pool import StaticPool
import pytest

# ensure project root is importable when pytest runs
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import app.models  # register models in SQLModel.metadata
import app.db as app_db
from app.main import app

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    SQLModel.metadata.create_all(engine)
    # make the app use the test engine
    try:
        app_db.engine = engine
    except Exception:
        pass
    return engine

@pytest.fixture
def session(engine):
    from sqlmodel import Session
    with Session(engine) as s:
        yield s

@pytest.fixture
def client(engine, session):
    def _get_session_override():
        from sqlmodel import Session
        with Session(engine) as s:
            yield s

    app.dependency_overrides[app_db.get_session] = _get_session_override
    from fastapi.testclient import TestClient as _TC
    with _TC(app) as c:
        yield c
    app.dependency_overrides.clear()
