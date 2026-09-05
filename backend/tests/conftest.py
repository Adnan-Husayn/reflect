"""Shared fixtures.

The database fixture uses SQLite on a temp file rather than Postgres, so the
unit suite stays fast and needs no running services. CI and deployment use
Postgres; the ORM uses generic JSON so the same models run on both.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.db.session import build_engine, get_db
from app.main import app

UNLOADED_MODELS = {"text": None, "audio": None, "facial": None, "speech": None}


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    """A fresh schema per test, with foreign keys enforced."""
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr("app.db.session.SessionLocal", TestingSession)
    monkeypatch.setattr("app.db.session.engine", engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestingSession
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


@pytest.fixture
def api(db_session, monkeypatch):
    """Client with a live database and no model checkpoints loaded."""
    monkeypatch.setattr("app.main.load_models", lambda: dict(UNLOADED_MODELS))
    with TestClient(app) as client:
        yield client
