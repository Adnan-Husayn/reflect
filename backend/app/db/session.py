"""Engine, session factory and the FastAPI dependency."""

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.db.models import Base, User

SEED_USER_EMAIL = "local@reflect.invalid"


def build_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, future=True)


engine = build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def _enforce_sqlite_foreign_keys(dbapi_connection, _record) -> None:
    """SQLite ignores foreign keys unless asked, which would silently disable
    the ON DELETE CASCADE the delete endpoints rely on."""
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Iterator[OrmSession]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_seed_user(db: OrmSession) -> User:
    """Resolve the single local user.

    Auth is deferred, but `user_id` exists from the first migration and every
    session-scoped query filters on it, so real accounts become a change to how
    the user is resolved — not a schema migration.
    """
    user = db.query(User).filter(User.email == SEED_USER_EMAIL).one_or_none()
    if user is None:
        user = User(email=SEED_USER_EMAIL)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def create_all() -> None:
    """Used by tests. Deployments run alembic instead."""
    Base.metadata.create_all(bind=engine)
