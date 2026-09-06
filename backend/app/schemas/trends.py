from datetime import date

from pydantic import BaseModel


class TrendBucket(BaseModel):
    """One day.

    `mean_valence`, `rolling_valence` and `conflict_rate` are null on a day
    that did not reach the reading minimum. The client must draw those days as
    a gap rather than substituting zero, which would read as neutral mood.
    """

    date: date
    n_sessions: int
    n_fused_readings: int
    mean_valence: float | None
    rolling_valence: float | None
    conflict_rate: float | None
    channel_counts: dict[str, int]
    sufficient: bool
    # Null on any day without a check-in. Check-ins are weekly, so most
    # days are null by design rather than by omission.
    checkin_score: int | None


class CorrelationOut(BaseModel):
    """Within-subject correlation between daily valence and PHQ-8.

    `r` is null below `minimum_pairs`, the same gap-not-zero rule the buckets
    use. PHQ-8 rises as wellbeing falls while valence does the opposite, so a
    negative r is the direction that would support the hypothesis.
    """

    r: float | None
    n: int
    minimum_pairs: int


class TrendsOut(BaseModel):
    start: date
    end: date
    buckets: list[TrendBucket]
    # Returned so the interface can state the rules it is drawing under,
    # instead of hardcoding numbers that would drift from the server.
    minimum_readings_per_day: int
    rolling_window_days: int
    correlation: CorrelationOut
