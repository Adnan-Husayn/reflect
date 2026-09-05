from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db.models import FusedReading, Reading, Session, SessionSummary
from app.db.session import ensure_seed_user
from app.schemas.emotion import CANONICAL_EMOTIONS
from app.utils.trends import (
    MINIMUM_READINGS_PER_DAY,
    ROLLING_WINDOW_DAYS,
    Bucket,
    SessionRollup,
    apply_rolling_valence,
    bucket_by_day,
    day_range,
)

DAY = date(2026, 9, 1)


def rollup(day: date, readings: int, valence: float | None, conflict: float | None = 0.0):
    return SessionRollup(
        day=day,
        n_fused_readings=readings,
        mean_valence=valence,
        conflict_rate=conflict,
        channel_counts={"face": readings * 2, "voice": readings},
    )


# ── bucketing ─────────────────────────────────────────────────────────


def test_every_day_in_the_range_gets_a_bucket():
    buckets = bucket_by_day([], DAY, DAY + timedelta(days=4))
    assert [bucket.day for bucket in buckets] == day_range(DAY, DAY + timedelta(days=4))
    assert len(buckets) == 5


def test_an_empty_range_returns_empty_buckets_not_zeros():
    """A day with no data must not be drawn as neutral mood."""
    buckets = bucket_by_day([], DAY, DAY + timedelta(days=2))
    assert all(bucket.mean_valence is None for bucket in buckets)
    assert all(bucket.n_sessions == 0 for bucket in buckets)
    assert all(not bucket.sufficient for bucket in buckets)


def test_a_thin_day_is_a_gap_rather_than_a_point():
    """One bad frame on a quiet Tuesday must not become a visible dip."""
    buckets = bucket_by_day([rollup(DAY, MINIMUM_READINGS_PER_DAY - 1, -1.0)], DAY, DAY)
    assert buckets[0].n_sessions == 1
    assert buckets[0].sufficient is False
    assert buckets[0].mean_valence is None
    assert buckets[0].conflict_rate is None


def test_a_day_at_exactly_the_minimum_counts():
    buckets = bucket_by_day([rollup(DAY, MINIMUM_READINGS_PER_DAY, 0.5)], DAY, DAY)
    assert buckets[0].sufficient is True
    assert buckets[0].mean_valence == pytest.approx(0.5)


def test_thin_sessions_can_add_up_to_a_sufficient_day():
    half = MINIMUM_READINGS_PER_DAY // 2 + 1
    buckets = bucket_by_day([rollup(DAY, half, 0.4), rollup(DAY, half, 0.6)], DAY, DAY)
    assert buckets[0].sufficient is True
    assert buckets[0].mean_valence == pytest.approx(0.5)


def test_daily_mean_is_weighted_by_readings_not_by_session():
    """A twenty-minute session must outweigh a thirty-second one."""
    buckets = bucket_by_day([rollup(DAY, 100, 0.8), rollup(DAY, 5, -1.0)], DAY, DAY)
    weighted = (0.8 * 100 + -1.0 * 5) / 105
    assert buckets[0].mean_valence == pytest.approx(weighted)
    # The unweighted mean of the two sessions would have been -0.1.
    assert buckets[0].mean_valence > 0.5


def test_channel_counts_accumulate_across_sessions():
    buckets = bucket_by_day([rollup(DAY, 30, 0.1), rollup(DAY, 20, 0.1)], DAY, DAY)
    assert buckets[0].channel_counts == {"face": 100, "voice": 50}


def test_sessions_outside_the_range_are_ignored():
    buckets = bucket_by_day([rollup(DAY - timedelta(days=5), 100, 1.0)], DAY, DAY)
    assert buckets[0].n_sessions == 0


def test_a_session_without_valence_still_counts_toward_the_day():
    buckets = bucket_by_day([rollup(DAY, 50, None)], DAY, DAY)
    assert buckets[0].n_fused_readings == 50
    assert buckets[0].sufficient is True
    assert buckets[0].mean_valence is None


# ── rolling window ────────────────────────────────────────────────────


def make_bucket(day: date, readings: int, valence: float | None):
    return Bucket(
        day=day,
        n_sessions=1,
        n_fused_readings=readings,
        mean_valence=valence,
        conflict_rate=None,
        channel_counts={},
        sufficient=valence is not None,
    )


def test_rolling_mean_covers_the_trailing_window_only():
    days = [make_bucket(DAY + timedelta(days=i), 100, 1.0) for i in range(10)]
    days[0] = make_bucket(DAY, 100, -1.0)
    rolled = apply_rolling_valence(days, window_days=ROLLING_WINDOW_DAYS)
    # By the eighth day the negative first day has fallen out of the window.
    assert rolled[7].rolling_valence == pytest.approx(1.0)
    assert rolled[6].rolling_valence < 1.0


def test_gap_days_contribute_nothing_to_the_rolling_mean():
    days = [
        make_bucket(DAY, 100, 1.0),
        make_bucket(DAY + timedelta(days=1), 2, None),
        make_bucket(DAY + timedelta(days=2), 100, 1.0),
    ]
    rolled = apply_rolling_valence(days)
    assert rolled[2].rolling_valence == pytest.approx(1.0)


def test_rolling_mean_is_none_when_the_window_holds_no_usable_day():
    days = [make_bucket(DAY + timedelta(days=i), 1, None) for i in range(3)]
    rolled = apply_rolling_valence(days)
    assert all(bucket.rolling_valence is None for bucket in rolled)


# ── endpoint ──────────────────────────────────────────────────────────


def scores(**weights: float) -> dict[str, float]:
    return {emotion: float(weights.get(emotion, 0.0)) for emotion in CANONICAL_EMOTIONS}


def seed_session(
    db,
    *,
    started: datetime,
    n_fused: int,
    valence: float | None,
    conflict: float | None,
    ended: bool = True,
    channel_counts: dict | None = None,
):
    user = ensure_seed_user(db)
    session = Session(user_id=user.id, started_at=started, ended_at=started if ended else None)
    db.add(session)
    db.flush()
    db.add(
        Reading(
            session_id=session.id,
            t=started,
            channel="face",
            label="joy",
            confidence=0.9,
            scores=scores(joy=1.0),
        )
    )
    db.add(
        FusedReading(
            session_id=session.id,
            t=started,
            label="joy",
            confidence=0.5,
            raw_confidence=0.9,
            attenuation=0.55,
            max_divergence=0.4,
            conflict=True,
            scores=scores(joy=1.0),
        )
    )
    if ended:
        db.add(
            SessionSummary(
                session_id=session.id,
                n_readings=1,
                n_fused_readings=n_fused,
                mean_valence=valence,
                conflict_rate=conflict,
                dominant_label="joy",
                channel_counts=channel_counts or {"face": 1},
                computed_at=started,
            )
        )
    db.commit()
    return session


def test_trends_returns_a_bucket_per_day_with_the_rules_it_used(api: TestClient):
    body = api.get("/trends?days=7").json()
    assert len(body["buckets"]) == 7
    assert body["minimum_readings_per_day"] == MINIMUM_READINGS_PER_DAY
    assert body["rolling_window_days"] == ROLLING_WINDOW_DAYS


def test_trends_with_no_sessions_returns_gaps_not_zeros(api: TestClient):
    body = api.get("/trends?days=3").json()
    assert all(bucket["mean_valence"] is None for bucket in body["buckets"])
    assert all(bucket["n_sessions"] == 0 for bucket in body["buckets"])


def test_a_recorded_session_appears_on_its_day(api: TestClient, db_session):
    today = datetime.now(UTC)
    with db_session() as db:
        seed_session(db, started=today, n_fused=50, valence=0.6, conflict=0.2)

    body = api.get("/trends?days=2").json()
    latest = body["buckets"][-1]
    assert latest["n_sessions"] == 1
    assert latest["n_fused_readings"] == 50
    assert latest["mean_valence"] == pytest.approx(0.6)
    assert latest["sufficient"] is True


def test_open_sessions_are_excluded(api: TestClient, db_session):
    """An in-progress session has no rollup and must not be drawn."""
    today = datetime.now(UTC)
    with db_session() as db:
        seed_session(db, started=today, n_fused=50, valence=0.6, conflict=0.2, ended=False)

    body = api.get("/trends?days=2").json()
    assert body["buckets"][-1]["n_sessions"] == 0


def test_a_thin_day_comes_back_as_a_gap(api: TestClient, db_session):
    today = datetime.now(UTC)
    with db_session() as db:
        seed_session(db, started=today, n_fused=2, valence=-1.0, conflict=1.0)

    latest = api.get("/trends?days=2").json()["buckets"][-1]
    assert latest["n_sessions"] == 1
    assert latest["sufficient"] is False
    assert latest["mean_valence"] is None


def test_the_day_range_is_bounded(api: TestClient):
    assert api.get("/trends?days=0").status_code == 422
    assert api.get("/trends?days=400").status_code == 422
