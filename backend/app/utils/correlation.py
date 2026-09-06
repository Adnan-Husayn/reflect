"""Pairing check-ins with daily valence, and the correlation between them.

This answers the question the project rests on: does the behavioural index
track a validated instrument? The honest version of that answer carries its own
sample size, because with weekly check-ins over a single term n lands somewhere
around 8-10 — a real result, and nowhere near significance.

Note the expected sign. PHQ-8 runs 0-24 where higher is worse; valence runs
-1..+1 where higher is better. If the index tracks the instrument at all, r
should be **negative**.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

# Below this many paired observations the coefficient is not reported at all.
# The same rule as the sparse-day gap in trends.py: a number computed from
# almost nothing invites more confidence than it can carry.
MINIMUM_PAIRS = 4


@dataclass(frozen=True)
class Correlation:
    r: float | None
    n: int
    minimum_pairs: int = MINIMUM_PAIRS

    @property
    def reportable(self) -> bool:
        return self.r is not None


def pair_observations(
    valence_by_day: Mapping[date, float | None],
    scores_by_day: Mapping[date, int],
) -> list[tuple[float, int]]:
    """Days that have both a usable valence and a check-in.

    A check-in on a day with no session contributes no pair, and neither does a
    day whose valence was withheld as a gap.
    """
    return [
        (valence, scores_by_day[day])
        for day, valence in valence_by_day.items()
        if valence is not None and day in scores_by_day
    ]


def pearson(pairs: Sequence[tuple[float, int]]) -> float | None:
    """Pearson r, or None when it is undefined.

    Undefined includes the case where either series is constant: with no
    variance there is nothing to correlate, and the usual formula divides by
    zero rather than returning a meaningful zero.
    """
    n = len(pairs)
    if n < 2:
        return None

    xs = [float(x) for x, _ in pairs]
    ys = [float(y) for _, y in pairs]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    variance_x = sum((x - mean_x) ** 2 for x in xs)
    variance_y = sum((y - mean_y) ** 2 for y in ys)
    denominator = math.sqrt(variance_x * variance_y)
    if denominator == 0:
        return None

    return max(-1.0, min(1.0, covariance / denominator))


def correlate(
    valence_by_day: Mapping[date, float | None],
    scores_by_day: Mapping[date, int],
    minimum_pairs: int = MINIMUM_PAIRS,
) -> Correlation:
    pairs = pair_observations(valence_by_day, scores_by_day)
    if len(pairs) < minimum_pairs:
        return Correlation(r=None, n=len(pairs), minimum_pairs=minimum_pairs)
    return Correlation(r=pearson(pairs), n=len(pairs), minimum_pairs=minimum_pairs)
