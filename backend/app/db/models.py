"""ORM models for session persistence.

**No raw media is stored anywhere in this schema.** There is deliberately no
LargeBinary/BYTEA column and no transcript column: the guarantee is structural,
not procedural, so it cannot be broken by a caller sending something unexpected.
`tests/test_no_media_persisted.py` asserts this by introspecting every column.

Session replay therefore shows emotion trajectories but never the words spoken.
That is the intended trade.
"""

import uuid
from datetime import UTC, date, datetime
from typing import Any, ClassVar

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.schemas.emotion import CANONICAL_EMOTIONS, CHANNELS


def _new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Timezone-aware UTC. Naive timestamps in longitudinal data cause bugs
    that only surface once the trends already look wrong."""
    return datetime.now(UTC)


def _one_of(column: str, allowed: tuple[str, ...]) -> str:
    values = ", ".join(f"'{value}'" for value in sorted(allowed))
    return f"{column} IN ({values})"


class Base(DeclarativeBase):
    # Generic JSON rather than Postgres JSONB: the same models then run on
    # SQLite, which keeps the unit suite fast and service-free while CI and
    # deployment use Postgres.
    type_annotation_map: ClassVar[dict[Any, Any]] = {dict: JSON}


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    # Nullable until real auth lands; the seeded local user has no password.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    checkins: Mapped[list["CheckIn"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    readings: Mapped[list["Reading"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    fused_readings: Mapped[list["FusedReading"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )
    summary: Mapped["SessionSummary | None"] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )

    # Trend queries in M4 filter by user over a date range.
    __table_args__ = (Index("ix_sessions_user_started", "user_id", "started_at"),)

    @property
    def is_open(self) -> bool:
        return self.ended_at is None


class Reading(Base):
    """One channel's reading at one instant."""

    __tablename__ = "readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    t: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    channel: Mapped[str] = mapped_column(String(8), nullable=False)
    label: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    scores: Mapped[dict] = mapped_column(JSON, nullable=False)

    session: Mapped[Session] = relationship(back_populates="readings")

    __table_args__ = (
        CheckConstraint(_one_of("channel", CHANNELS), name="ck_readings_channel"),
        CheckConstraint(_one_of("label", CANONICAL_EMOTIONS), name="ck_readings_label"),
        Index("ix_readings_session_t", "session_id", "t"),
    )


class FusedReading(Base):
    """The composite reading, and the divergence that attenuated it."""

    __tablename__ = "fused_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    t: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    label: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    raw_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    attenuation: Mapped[float] = mapped_column(Float, nullable=False)
    # Null when fewer than two channels were available, matching the engine's
    # `insufficient_channels` status rather than recording a misleading zero.
    max_divergence: Mapped[float | None] = mapped_column(Float, nullable=True)
    conflict: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scores: Mapped[dict] = mapped_column(JSON, nullable=False)

    session: Mapped[Session] = relationship(back_populates="fused_readings")

    __table_args__ = (
        CheckConstraint(_one_of("label", CANONICAL_EMOTIONS), name="ck_fused_label"),
        Index("ix_fused_session_t", "session_id", "t"),
    )


class SessionSummary(Base):
    """Rollup computed once at session end.

    A ten-minute session produces roughly 300 facial and 120 audio readings, so
    M4's trend queries read this table rather than scanning those rows.
    """

    __tablename__ = "session_summaries"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    n_readings: Mapped[int] = mapped_column(Integer, nullable=False)
    n_fused_readings: Mapped[int] = mapped_column(Integer, nullable=False)
    # Mean over FUSED readings only — see app/utils/valence.py:mean_valence.
    mean_valence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Proportion of fused readings flagged as a conflict.
    conflict_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    dominant_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Reading count per channel. Counts, not proportions: the question this
    # answers is whether a channel was available at all (a denied camera gives
    # face 0), and proportions would merely restate the sampling rates.
    channel_counts: Mapped[dict] = mapped_column(JSON, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[Session] = relationship(back_populates="summary")


class CheckIn(Base):
    """A self-report score from a validated instrument (PHQ-8 / GAD-7).

    Present from M1 with a write path, because check-ins need calendar time to
    accumulate — a table nobody can write to would collect nothing.
    """

    __tablename__ = "checkins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    taken_on: Mapped[date] = mapped_column(Date, nullable=False)
    instrument: Mapped[str] = mapped_column(String(16), nullable=False)
    responses: Mapped[dict] = mapped_column(JSON, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="checkins")

    __table_args__ = (
        UniqueConstraint("user_id", "taken_on", "instrument", name="uq_checkin_per_day"),
        Index("ix_checkins_user_taken", "user_id", "taken_on"),
    )
