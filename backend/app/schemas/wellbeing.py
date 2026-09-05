from datetime import date

from pydantic import BaseModel


class DayOut(BaseModel):
    """One day's observations. Shares are null on a day below the minimum."""

    date: date
    n_readings: int
    low_valence_share: float | None
    conflict_share: float | None
    sufficient: bool


class PromptOut(BaseModel):
    key: str
    observation: str
    suggestion: str


class WellbeingOut(BaseModel):
    """Observations over the trailing window, and the inputs behind them.

    The components are returned alongside the status rather than instead of it,
    so the interface can never render a headline without what produced it.
    """

    status: str
    days_with_data: int
    low_valence_days: int
    conflict_days: int
    sustained_low_valence: bool
    sustained_conflict: bool
    window_days: int
    sustained_days_required: int
    minimum_days: int
    days: list[DayOut]
    prompts: list[PromptOut]
    # Echoed so the interface states the rules it is reporting under rather
    # than hardcoding numbers that would drift from the server.
    low_valence_threshold: float
    low_valence_share_threshold: float
    conflict_share_threshold: float
