"""The tracked construct, defined rather than invented.

Two observations over a trailing window, each computed from data the session
rollups already produce:

- **low-valence share** — the proportion of a day's fused readings whose
  valence falls below a configured threshold
- **conflict share** — the proportion flagged as a cross-channel conflict

Neither is a state. A day qualifies or it does not, and a *sustained* pattern
requires the day to qualify on at least N days of the window. **A single bad
day is never a signal** — that rule is the whole reason this module exists
rather than a threshold applied to yesterday's number.

Every constant comes from Settings and every default is provisional, to be
re-derived from the RAVDESS evaluation exactly as the fusion weights will be.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date

from app.utils.valence import valence_of


@dataclass(frozen=True)
class ReadingValence:
    day: date
    valence: float
    conflict: bool


@dataclass
class DayObservation:
    day: date
    n_readings: int = 0
    low_valence_share: float | None = None
    conflict_share: float | None = None
    sufficient: bool = False

    def qualifies_low_valence(self, share_threshold: float) -> bool:
        return self.sufficient and (self.low_valence_share or 0.0) >= share_threshold

    def qualifies_conflict(self, share_threshold: float) -> bool:
        return self.sufficient and (self.conflict_share or 0.0) >= share_threshold


@dataclass
class Assessment:
    """Observations and their inputs. Never a state, never a diagnosis."""

    status: str
    days_with_data: int
    low_valence_days: int
    conflict_days: int
    sustained_low_valence: bool
    sustained_conflict: bool
    window_days: int
    sustained_days_required: int
    minimum_days: int
    days: list[DayObservation] = field(default_factory=list)


def to_reading_valences(
    rows: Iterable[tuple[date, dict[str, float], bool]],
) -> list[ReadingValence]:
    """Map stored fused readings onto their valence, skipping unusable ones."""
    observations = []
    for day, scores, conflict in rows:
        try:
            observations.append(ReadingValence(day, valence_of(scores), bool(conflict)))
        except ValueError:
            # A score vector with no positive mass cannot be valenced. Dropping
            # it is right: counting it as neutral would invent an observation.
            continue
    return observations


def summarise_days(
    readings: Sequence[ReadingValence],
    days: Sequence[date],
    minimum_readings: int,
    low_valence_threshold: float,
) -> list[DayObservation]:
    observations = {day: DayObservation(day=day) for day in days}
    low = dict.fromkeys(days, 0)
    conflicted = dict.fromkeys(days, 0)

    for reading in readings:
        observation = observations.get(reading.day)
        if observation is None:
            continue
        observation.n_readings += 1
        if reading.valence < low_valence_threshold:
            low[reading.day] += 1
        if reading.conflict:
            conflicted[reading.day] += 1

    for day, observation in observations.items():
        observation.sufficient = observation.n_readings >= minimum_readings
        if observation.sufficient:
            observation.low_valence_share = low[day] / observation.n_readings
            observation.conflict_share = conflicted[day] / observation.n_readings

    return [observations[day] for day in days]


def assess(
    observations: Sequence[DayObservation],
    *,
    low_valence_share: float,
    conflict_share: float,
    sustained_days: int,
    minimum_days: int,
) -> Assessment:
    """Fold the daily observations into what can honestly be said about them."""
    with_data = [observation for observation in observations if observation.sufficient]
    low_days = sum(1 for observation in with_data if observation.qualifies_low_valence(low_valence_share))
    conflict_days = sum(1 for observation in with_data if observation.qualifies_conflict(conflict_share))

    sustained_low = low_days >= sustained_days
    sustained_conflict = conflict_days >= sustained_days

    if len(with_data) < minimum_days:
        # Withheld rather than reported as settled. Reporting "nothing to see"
        # from two days of data would be a reassurance nobody measured.
        status = "insufficient_data"
    elif sustained_low or sustained_conflict:
        status = "observations"
    else:
        status = "steady"

    return Assessment(
        status=status,
        days_with_data=len(with_data),
        low_valence_days=low_days,
        conflict_days=conflict_days,
        sustained_low_valence=status == "observations" and sustained_low,
        sustained_conflict=status == "observations" and sustained_conflict,
        window_days=len(observations),
        sustained_days_required=sustained_days,
        minimum_days=minimum_days,
        days=list(observations),
    )
