"""Bucketing and rolling means for the trends view.

Pure functions: they take already-loaded summaries and return buckets, so the
rules below are testable without a database.

The failure mode these rules exist to prevent: a day holding one 30-second
session and a day holding four 20-minute sessions are not comparable, and a
naive daily mean draws them at the same weight. A single bad frame on a quiet
Tuesday would then show up as a visible dip in someone's mood trend.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

# A day holding fewer fused readings than this is reported as a gap rather than
# a point. Named rather than inlined because it is a judgement call that the
# report has to state and defend.
MINIMUM_READINGS_PER_DAY = 20

ROLLING_WINDOW_DAYS = 7


@dataclass(frozen=True)
class SessionRollup:
    """One completed session's summary, as the endpoint loads it."""

    day: date
    n_fused_readings: int
    mean_valence: float | None
    conflict_rate: float | None
    channel_counts: dict[str, int]


@dataclass
class Bucket:
    day: date
    n_sessions: int = 0
    n_fused_readings: int = 0
    mean_valence: float | None = None
    rolling_valence: float | None = None
    conflict_rate: float | None = None
    channel_counts: dict[str, int] = field(default_factory=dict)
    sufficient: bool = False


def _weighted_mean(pairs: Sequence[tuple[float, int]]) -> float | None:
    """Mean of (value, weight), or None when nothing carries weight."""
    total_weight = sum(weight for _, weight in pairs)
    if total_weight <= 0:
        return None
    return sum(value * weight for value, weight in pairs) / total_weight


def day_range(start: date, end: date) -> list[date]:
    if end < start:
        return []
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def bucket_by_day(
    rollups: Iterable[SessionRollup],
    start: date,
    end: date,
    minimum_readings: int = MINIMUM_READINGS_PER_DAY,
) -> list[Bucket]:
    """One bucket per day in the range, including days with no sessions.

    Daily means are weighted by fused-reading count, so a long session counts
    for more than a short one on the same day.
    """
    buckets = {day: Bucket(day=day) for day in day_range(start, end)}
    valence_pairs: dict[date, list[tuple[float, int]]] = {day: [] for day in buckets}
    conflict_pairs: dict[date, list[tuple[float, int]]] = {day: [] for day in buckets}

    for rollup in rollups:
        bucket = buckets.get(rollup.day)
        if bucket is None:
            continue
        bucket.n_sessions += 1
        bucket.n_fused_readings += rollup.n_fused_readings
        for channel, count in rollup.channel_counts.items():
            bucket.channel_counts[channel] = bucket.channel_counts.get(channel, 0) + count
        if rollup.mean_valence is not None:
            valence_pairs[rollup.day].append((rollup.mean_valence, rollup.n_fused_readings))
        if rollup.conflict_rate is not None:
            conflict_pairs[rollup.day].append((rollup.conflict_rate, rollup.n_fused_readings))

    for day, bucket in buckets.items():
        bucket.sufficient = bucket.n_fused_readings >= minimum_readings
        if not bucket.sufficient:
            # Left as None on purpose: the chart draws a gap, not a point. A
            # thin day must not be able to bend the line.
            continue
        bucket.mean_valence = _weighted_mean(valence_pairs[day])
        bucket.conflict_rate = _weighted_mean(conflict_pairs[day])

    return [buckets[day] for day in day_range(start, end)]


def apply_rolling_valence(buckets: Sequence[Bucket], window_days: int = ROLLING_WINDOW_DAYS) -> list[Bucket]:
    """Rolling mean over the trailing window, weighted by reading count.

    Weighting across the window rather than averaging the daily means keeps a
    thin-but-sufficient day from counting as much as a heavy one, and days
    reported as gaps contribute nothing at all.
    """
    for index, bucket in enumerate(buckets):
        window = buckets[max(0, index - window_days + 1) : index + 1]
        pairs = [
            (day.mean_valence, day.n_fused_readings)
            for day in window
            if day.sufficient and day.mean_valence is not None
        ]
        bucket.rolling_valence = _weighted_mean(pairs)
    return list(buckets)


def build_trends(
    rollups: Iterable[SessionRollup],
    start: date,
    end: date,
    minimum_readings: int = MINIMUM_READINGS_PER_DAY,
    window_days: int = ROLLING_WINDOW_DAYS,
) -> list[Bucket]:
    return apply_rolling_valence(bucket_by_day(rollups, start, end, minimum_readings), window_days)
