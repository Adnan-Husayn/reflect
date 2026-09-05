from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.models import FusedReading, Session, User
from app.schemas.emotion import CANONICAL_EMOTIONS
from app.utils.distress import DayObservation, assess, summarise_days, to_reading_valences

START = date(2026, 9, 1)
WINDOW = [START + timedelta(days=offset) for offset in range(7)]


def scores(**weights: float) -> dict[str, float]:
    return {emotion: float(weights.get(emotion, 0.0)) for emotion in CANONICAL_EMOTIONS}


def observation(offset: int, low: float, conflict: float, n: int = 60) -> DayObservation:
    return DayObservation(
        day=START + timedelta(days=offset),
        n_readings=n,
        low_valence_share=low,
        conflict_share=conflict,
        sufficient=True,
    )


def run(days, **overrides):
    settings = {
        "low_valence_share": 0.4,
        "conflict_share": 0.4,
        "sustained_days": 3,
        "minimum_days": 3,
    }
    return assess(days, **{**settings, **overrides})


# ── a single bad day is never a signal ────────────────────────────────


def test_one_bad_day_does_not_trigger_a_sustained_state():
    """The whole reason this module exists rather than a threshold on
    yesterday's number."""
    days = [observation(index, 0.05, 0.05) for index in range(6)]
    days.append(observation(6, 0.95, 0.95))

    result = run(days)
    assert result.status == "steady"
    assert result.sustained_low_valence is False
    assert result.sustained_conflict is False
    assert result.low_valence_days == 1


def test_two_bad_days_still_do_not_reach_the_threshold():
    days = [observation(index, 0.05, 0.05) for index in range(5)]
    days += [observation(5, 0.9, 0.05), observation(6, 0.9, 0.05)]
    assert run(days).sustained_low_valence is False


def test_the_configured_number_of_qualifying_days_triggers_it():
    days = [observation(index, 0.9, 0.05) for index in range(3)]
    days += [observation(index, 0.05, 0.05) for index in range(3, 7)]

    result = run(days)
    assert result.status == "observations"
    assert result.sustained_low_valence is True
    assert result.sustained_conflict is False
    assert result.low_valence_days == 3


def test_the_two_observations_are_independent():
    days = [observation(index, 0.05, 0.9) for index in range(4)]
    days += [observation(index, 0.05, 0.05) for index in range(4, 7)]

    result = run(days)
    assert result.sustained_conflict is True
    assert result.sustained_low_valence is False


def test_a_day_exactly_at_the_share_threshold_qualifies():
    days = [observation(index, 0.4, 0.0) for index in range(3)]
    days += [observation(index, 0.0, 0.0) for index in range(3, 7)]
    assert run(days).sustained_low_valence is True


# ── withheld rather than reassuring ───────────────────────────────────


def test_below_the_minimum_days_nothing_is_reported_in_either_direction():
    """Two days of data must not produce 'steady' — that is a reassurance
    nobody measured."""
    result = run([observation(0, 0.05, 0.05), observation(1, 0.05, 0.05)])
    assert result.status == "insufficient_data"
    assert result.days_with_data == 2


def test_bad_days_below_the_minimum_are_also_withheld():
    result = run([observation(0, 0.95, 0.95), observation(1, 0.95, 0.95)])
    assert result.status == "insufficient_data"
    assert result.sustained_low_valence is False


def test_days_without_enough_readings_do_not_count_as_days_with_data():
    thin = DayObservation(day=START, n_readings=3, sufficient=False)
    assert run([thin, observation(1, 0.05, 0.05), observation(2, 0.05, 0.05)]).days_with_data == 2


# ── the thresholds come from settings ─────────────────────────────────


def test_the_share_threshold_is_a_parameter_not_a_literal():
    days = [observation(index, 0.3, 0.0) for index in range(7)]
    assert run(days, low_valence_share=0.4).sustained_low_valence is False
    assert run(days, low_valence_share=0.25).sustained_low_valence is True


def test_the_sustained_day_count_is_a_parameter_not_a_literal():
    days = [observation(index, 0.9, 0.0) for index in range(2)]
    days += [observation(index, 0.0, 0.0) for index in range(2, 7)]
    assert run(days, sustained_days=3).sustained_low_valence is False
    assert run(days, sustained_days=2).sustained_low_valence is True


def test_the_defaults_all_come_from_settings():
    settings = get_settings()
    for name in (
        "distress_window_days",
        "distress_low_valence",
        "distress_low_valence_share",
        "distress_conflict_share",
        "distress_sustained_days",
        "distress_minimum_days",
        "distress_minimum_readings_per_day",
    ):
        assert hasattr(settings, name), f"{name} must be configurable, not a literal"


# ── daily summarisation ───────────────────────────────────────────────


def test_shares_are_computed_per_reading_not_from_a_daily_mean():
    """Half the readings deeply negative and half mildly positive averages to
    roughly neutral; the share is what survives that."""
    readings = to_reading_valences(
        [(START, scores(sadness=1.0), False)] * 30 + [(START, scores(joy=1.0), False)] * 30
    )
    day = summarise_days(readings, [START], minimum_readings=20, low_valence_threshold=-0.2)[0]
    assert day.low_valence_share == pytest.approx(0.5)


def test_a_thin_day_reports_no_shares_at_all():
    readings = to_reading_valences([(START, scores(sadness=1.0), True)] * 5)
    day = summarise_days(readings, [START], minimum_readings=20, low_valence_threshold=-0.2)[0]
    assert day.sufficient is False
    assert day.low_valence_share is None
    assert day.conflict_share is None


def test_an_unusable_score_vector_is_dropped_rather_than_counted_neutral():
    """Counting it as neutral would invent an observation."""
    readings = to_reading_valences([(START, scores(), False), (START, scores(joy=1.0), False)])
    assert len(readings) == 1


def test_every_day_in_the_window_appears_even_with_no_readings():
    days = summarise_days([], WINDOW, minimum_readings=20, low_valence_threshold=-0.2)
    assert len(days) == 7
    assert all(day.n_readings == 0 and not day.sufficient for day in days)


# ── endpoint ──────────────────────────────────────────────────────────


def seed_readings(db, user_email: str, offsets_and_scores):
    user = db.query(User).filter(User.email == user_email).one()
    now = datetime.now(UTC)
    for offset, score_vector, conflict, count in offsets_and_scores:
        started = now - timedelta(days=offset)
        session = Session(user_id=user.id, started_at=started, ended_at=started)
        db.add(session)
        db.flush()
        for _ in range(count):
            db.add(
                FusedReading(
                    session_id=session.id,
                    t=started,
                    label="sadness",
                    confidence=0.5,
                    raw_confidence=0.8,
                    attenuation=0.6,
                    max_divergence=0.5,
                    conflict=conflict,
                    scores=score_vector,
                )
            )
    db.commit()


def test_a_fresh_account_gets_insufficient_data_not_a_low_score(api: TestClient):
    body = api.get("/wellbeing").json()
    assert body["status"] == "insufficient_data"
    assert body["days_with_data"] == 0
    assert body["sustained_low_valence"] is False


def test_the_response_carries_the_components_behind_the_status(api: TestClient):
    body = api.get("/wellbeing").json()
    for field in (
        "low_valence_days",
        "conflict_days",
        "days_with_data",
        "window_days",
        "sustained_days_required",
        "low_valence_threshold",
        "low_valence_share_threshold",
    ):
        assert field in body, f"{field} must accompany the status"
    assert len(body["days"]) == body["window_days"]


def test_sustained_low_valence_is_reported_from_real_readings(api: TestClient, db_session):
    with db_session() as db:
        seed_readings(
            db,
            "tester@example.com",
            [(offset, scores(sadness=1.0), False, 40) for offset in range(4)],
        )

    body = api.get("/wellbeing").json()
    assert body["status"] == "observations"
    assert body["sustained_low_valence"] is True
    assert any(prompt["key"] == "sustained_low_valence" for prompt in body["prompts"])


def test_a_settled_week_reports_steady_rather_than_nothing(api: TestClient, db_session):
    with db_session() as db:
        seed_readings(
            db,
            "tester@example.com",
            [(offset, scores(joy=1.0), False, 40) for offset in range(4)],
        )

    body = api.get("/wellbeing").json()
    assert body["status"] == "steady"
    assert body["prompts"][0]["key"] == "steady"


def test_wellbeing_requires_an_account(anon: TestClient):
    assert anon.get("/wellbeing").status_code == 401


def test_one_account_does_not_see_another_accounts_readings(api: TestClient, db_session):
    with db_session() as db:
        seed_readings(
            db,
            "tester@example.com",
            [(offset, scores(sadness=1.0), False, 40) for offset in range(4)],
        )
    assert api.get("/wellbeing").json()["status"] == "observations"

    api.post("/auth/logout")
    api.cookies.clear()
    api.post("/auth/register", json={"email": "second@example.com", "password": "another-long-password"})

    assert api.get("/wellbeing").json()["status"] == "insufficient_data"
