from datetime import date, timedelta

import pytest

from app.utils.correlation import MINIMUM_PAIRS, correlate, pair_observations, pearson

START = date(2026, 9, 1)


def day(offset: int) -> date:
    return START + timedelta(days=offset)


# ── pairing ───────────────────────────────────────────────────────────


def test_only_days_with_both_a_valence_and_a_checkin_are_paired():
    pairs = pair_observations(
        {day(0): 0.5, day(1): 0.2, day(2): -0.3},
        {day(0): 4, day(2): 12},
    )
    assert pairs == [(0.5, 4), (-0.3, 12)]


def test_a_gap_day_contributes_no_pair():
    """A day the buckets withheld has no valence to correlate against."""
    assert pair_observations({day(0): None}, {day(0): 8}) == []


def test_a_checkin_without_a_session_contributes_no_pair():
    assert pair_observations({}, {day(0): 8}) == []


# ── pearson ───────────────────────────────────────────────────────────


def test_a_perfect_inverse_relationship_is_minus_one():
    """The direction that would support the hypothesis: PHQ-8 rises as
    wellbeing falls, while valence does the opposite."""
    pairs = [(1.0 - index * 0.2, index * 4) for index in range(5)]
    assert pearson(pairs) == pytest.approx(-1.0)


def test_a_perfect_positive_relationship_is_plus_one():
    assert pearson([(index * 0.2, index * 4) for index in range(5)]) == pytest.approx(1.0)


def test_an_unrelated_series_is_near_zero():
    assert pearson([(0.5, 4), (-0.5, 4), (0.5, 12), (-0.5, 12)]) == pytest.approx(0.0)


def test_a_constant_series_has_no_correlation_rather_than_zero():
    """With no variance there is nothing to correlate; the usual formula
    divides by zero rather than returning a meaningful zero."""
    assert pearson([(0.5, 4), (0.5, 9), (0.5, 12)]) is None
    assert pearson([(0.1, 8), (0.6, 8), (-0.2, 8)]) is None


def test_a_single_pair_has_no_correlation():
    assert pearson([(0.5, 4)]) is None


def test_r_stays_within_bounds():
    pairs = [(0.9, 1), (0.4, 8), (-0.2, 15), (-0.8, 23), (0.1, 11)]
    assert -1.0 <= pearson(pairs) <= 1.0


# ── the reporting rule ────────────────────────────────────────────────


def test_the_coefficient_is_withheld_below_the_minimum():
    """A number computed from almost nothing invites more confidence than it
    can carry — the same rule as the sparse-day gap in trends."""
    valence = {day(index): 0.5 - index * 0.1 for index in range(MINIMUM_PAIRS - 1)}
    scores = {day(index): index * 3 for index in range(MINIMUM_PAIRS - 1)}

    result = correlate(valence, scores)
    assert result.r is None
    assert result.n == MINIMUM_PAIRS - 1
    assert result.reportable is False


def test_the_coefficient_is_reported_at_the_minimum():
    valence = {day(index): 0.5 - index * 0.1 for index in range(MINIMUM_PAIRS)}
    scores = {day(index): index * 3 for index in range(MINIMUM_PAIRS)}

    result = correlate(valence, scores)
    assert result.r == pytest.approx(-1.0)
    assert result.n == MINIMUM_PAIRS
    assert result.reportable is True


def test_n_is_reported_even_when_r_is_withheld():
    """The sample size is the honest part of the answer, so it is always
    available even when the coefficient is not."""
    result = correlate({day(0): 0.5}, {day(0): 4})
    assert result.r is None
    assert result.n == 1
    assert result.minimum_pairs == MINIMUM_PAIRS
