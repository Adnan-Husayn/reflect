"""Request and response models for session persistence.

Every request model sets `extra="forbid"`. That is the load-bearing privacy
guard: without it a client could add a `transcript` or `audio` field to
otherwise valid JSON, and the schema would accept and ignore it today but
happily persist it the moment somebody adds a matching column in good faith.
Forbidding unknown fields makes that a 422 instead of a silent regression.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.instruments import INSTRUMENTS
from app.instruments.phq8 import score_responses
from app.schemas.emotion import CANONICAL_EMOTIONS, CHANNELS


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _validate_scores(scores: dict[str, float]) -> dict[str, float]:
    unknown = set(scores) - set(CANONICAL_EMOTIONS)
    if unknown:
        raise ValueError(f"Unknown emotion labels: {', '.join(sorted(unknown))}.")
    if any(value < 0 for value in scores.values()):
        raise ValueError("Emotion scores cannot be negative.")
    if sum(scores.values()) <= 0:
        raise ValueError("Emotion scores must contain at least one positive value.")
    return scores


class ReadingIn(StrictModel):
    t: datetime
    channel: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    scores: dict[str, float]

    @field_validator("channel")
    @classmethod
    def known_channel(cls, channel: str) -> str:
        if channel not in CHANNELS:
            raise ValueError(f"Channel must be one of: {', '.join(CHANNELS)}.")
        return channel

    @field_validator("label")
    @classmethod
    def known_label(cls, label: str) -> str:
        if label not in CANONICAL_EMOTIONS:
            raise ValueError(f"Unknown emotion label: {label}.")
        return label

    @field_validator("scores")
    @classmethod
    def valid_scores(cls, scores: dict[str, float]) -> dict[str, float]:
        return _validate_scores(scores)


class FusedReadingIn(StrictModel):
    t: datetime
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    raw_confidence: float = Field(ge=0.0, le=1.0)
    attenuation: float = Field(ge=0.0, le=1.0)
    max_divergence: float | None = Field(default=None, ge=0.0, le=1.0)
    conflict: bool = False
    scores: dict[str, float]

    @field_validator("label")
    @classmethod
    def known_label(cls, label: str) -> str:
        if label not in CANONICAL_EMOTIONS:
            raise ValueError(f"Unknown emotion label: {label}.")
        return label

    @field_validator("scores")
    @classmethod
    def valid_scores(cls, scores: dict[str, float]) -> dict[str, float]:
        return _validate_scores(scores)


class ReadingBatch(StrictModel):
    """Readings arrive in batches: a live session emits a facial reading every
    two seconds and an audio segment every five, and one request per reading
    would triple the request volume for no benefit."""

    readings: list[ReadingIn] = Field(default_factory=list)
    fused: list[FusedReadingIn] = Field(default_factory=list)


class BatchAccepted(BaseModel):
    session_id: str
    readings_added: int
    fused_added: int


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    started_at: datetime
    ended_at: datetime | None


class SummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    n_readings: int
    n_fused_readings: int
    mean_valence: float | None
    conflict_rate: float | None
    dominant_label: str | None
    channel_counts: dict[str, int]
    computed_at: datetime


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    t: datetime
    channel: str
    label: str
    confidence: float
    scores: dict[str, float]


class FusedReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    t: datetime
    label: str
    confidence: float
    raw_confidence: float
    attenuation: float
    max_divergence: float | None
    conflict: bool
    scores: dict[str, float]


class SessionDetail(SessionOut):
    summary: SummaryOut | None
    readings: list[ReadingOut]
    fused_readings: list[FusedReadingOut]


class SessionListItem(SessionOut):
    summary: SummaryOut | None


class CheckInIn(StrictModel):
    """One self-report submission.

    `score` is recomputed from `responses` and the submission is rejected if the
    two disagree, rather than storing what the client claimed. Before this, a
    PHQ-8 with two answers and a score of 9999 was a valid request.
    """

    taken_on: date
    instrument: str
    responses: dict[str, int]
    score: int = Field(ge=0)

    @field_validator("instrument")
    @classmethod
    def known_instrument(cls, instrument: str) -> str:
        if instrument not in INSTRUMENTS:
            raise ValueError(f"Instrument must be one of: {', '.join(sorted(INSTRUMENTS))}.")
        return instrument

    @model_validator(mode="after")
    def score_matches_responses(self) -> "CheckInIn":
        instrument = INSTRUMENTS.get(self.instrument)
        if instrument is None:
            return self
        computed = score_responses(instrument, self.responses)
        if computed != self.score:
            raise ValueError(f"Score {self.score} does not match the responses, which total {computed}.")
        return self


class CheckInOut(BaseModel):
    id: str
    taken_on: date
    instrument: str
    responses: dict[str, int]
    score: int


class DeletionReceipt(BaseModel):
    """Returned by the delete endpoints so a withdrawal is auditable."""

    deleted_sessions: int
    deleted_readings: int
    deleted_fused_readings: int
    deleted_checkins: int
