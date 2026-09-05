"""Shared fixtures.

The database fixture uses SQLite on a temp file rather than Postgres, so the
unit suite stays fast and needs no running services. CI and deployment use
Postgres; the ORM uses generic JSON so the same models run on both.
"""

import os

# Settings are built when app.config is first imported, and secret_key has no
# default by design, so this must run before any app import below.
os.environ.setdefault("SECRET_KEY", "test-secret-not-used-anywhere-real")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.db.session import build_engine, get_db
from app.main import app
from app.security import _attempts

UNLOADED_MODELS = {"text": None, "audio": None, "facial": None, "speech": None}
PASSWORD = "a-sufficiently-long-password"


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
def anon(db_session, monkeypatch):
    """A client with a live database, no models loaded, and nobody signed in."""
    monkeypatch.setattr("app.main.load_models", lambda: dict(UNLOADED_MODELS))
    # Login throttling is process-global; reset it so one test cannot lock out
    # another that happens to use the same address.
    _attempts.clear()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def api(anon):
    """Signed in. Most endpoints require an account, so this is the default."""
    response = anon.post("/auth/register", json={"email": "tester@example.com", "password": PASSWORD})
    assert response.status_code == 201, response.text
    return anon
