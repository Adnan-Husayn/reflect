"""Regressions for the audit findings.

Each of these covers behaviour that was wrong while every test passed, because
nothing exercised the path end to end.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.db.models import Session, User
from app.routers.sessions import close_abandoned_sessions
from app.schemas.emotion import CANONICAL_EMOTIONS


def scores(**weights: float) -> dict[str, float]:
    return {emotion: float(weights.get(emotion, 0.0)) for emotion in CANONICAL_EMOTIONS}


def fused(offset_seconds: int, label: str, **weights: float) -> dict:
    return {
        "t": (datetime.now(UTC) - timedelta(seconds=offset_seconds)).isoformat(),
        "label": label,
        "confidence": 0.5,
        "raw_confidence": 0.8,
        "attenuation": 0.6,
        "max_divergence": 0.4,
        "conflict": False,
        "scores": scores(**weights),
    }


def backdate(db_session, session_id: str, hours: int) -> None:
    with db_session() as db:
        session = db.query(Session).filter(Session.id == session_id).one()
        session.started_at = datetime.now(UTC) - timedelta(hours=hours)
        db.commit()


# ── abandoned sessions ────────────────────────────────────────────────


def test_an_abandoned_session_is_closed_and_summarised(api: TestClient, db_session):
    """Closing the tab mid-session left ended_at NULL forever. Trends and
    wellbeing both require a summary, so the session was silently dropped from
    everything rather than reported as incomplete."""
    session_id = api.post("/sessions").json()["id"]
    api.post(f"/sessions/{session_id}/readings", json={"readings": [], "fused": [fused(5, "joy", joy=1.0)]})
    backdate(db_session, session_id, hours=24)

    with db_session() as db:
        user = db.query(User).filter(User.email == "tester@example.com").one()
        closed = close_abandoned_sessions(db, user, older_than_hours=6)

    assert closed == 1
    body = api.get(f"/sessions/{session_id}").json()
    assert body["ended_at"] is not None
    assert body["summary"] is not None
    assert body["summary"]["n_fused_readings"] == 1


def test_a_recent_open_session_is_left_alone(api: TestClient, db_session):
    session_id = api.post("/sessions").json()["id"]

    with db_session() as db:
        user = db.query(User).filter(User.email == "tester@example.com").one()
        assert close_abandoned_sessions(db, user, older_than_hours=6) == 0

    assert api.get(f"/sessions/{session_id}").json()["ended_at"] is None


def test_opening_a_session_sweeps_the_abandoned_ones(api: TestClient, db_session):
    """The sweep runs on the next open, so it needs no scheduler."""
    stale = api.post("/sessions").json()["id"]
    backdate(db_session, stale, hours=48)

    api.post("/sessions")

    assert api.get(f"/sessions/{stale}").json()["summary"] is not None


def test_the_sweep_does_not_touch_another_account(api: TestClient, db_session):
    stale = api.post("/sessions").json()["id"]
    backdate(db_session, stale, hours=48)

    api.post("/auth/logout")
    api.cookies.clear()
    api.post("/auth/register", json={"email": "other@example.com", "password": "another-long-password"})
    api.post("/sessions")

    with db_session() as db:
        assert db.query(Session).filter(Session.id == stale).one().ended_at is None


# ── bounded responses ─────────────────────────────────────────────────


def test_the_session_list_is_paginated(api: TestClient):
    for _ in range(5):
        api.post("/sessions")

    assert len(api.get("/sessions?limit=2").json()) == 2
    assert len(api.get("/sessions?limit=2&offset=4").json()) >= 1


def test_the_page_size_is_bounded(api: TestClient):
    assert api.get("/sessions?limit=500").status_code == 422
    assert api.get("/sessions?offset=-1").status_code == 422


# ── windowed queries ──────────────────────────────────────────────────


def test_trends_ignores_sessions_outside_the_requested_range(api: TestClient, db_session):
    """The range is applied in the query now, not after loading everything."""
    old = api.post("/sessions").json()["id"]
    api.post(f"/sessions/{old}/readings", json={"readings": [], "fused": [fused(0, "joy", joy=1.0)]})
    api.post(f"/sessions/{old}/end")
    backdate(db_session, old, hours=24 * 60)

    body = api.get("/trends?days=7").json()
    assert sum(bucket["n_sessions"] for bucket in body["buckets"]) == 0


def test_wellbeing_ignores_readings_outside_its_window(api: TestClient, db_session):
    """Wellbeing buckets by reading timestamp, so the readings themselves are
    what must fall outside the window — not merely the session that held them."""
    two_months = 60 * 24 * 3600
    old = api.post("/sessions").json()["id"]
    api.post(
        f"/sessions/{old}/readings",
        json={
            "readings": [],
            "fused": [fused(two_months, "sadness", sadness=1.0) for _ in range(40)],
        },
    )
    api.post(f"/sessions/{old}/end")
    backdate(db_session, old, hours=24 * 60)

    body = api.get("/wellbeing").json()
    assert body["days_with_data"] == 0
    assert body["status"] == "insufficient_data"


def test_wellbeing_still_sees_readings_inside_the_window(api: TestClient):
    """The counterpart: the filter must not exclude everything."""
    session_id = api.post("/sessions").json()["id"]
    api.post(
        f"/sessions/{session_id}/readings",
        json={"readings": [], "fused": [fused(60, "sadness", sadness=1.0) for _ in range(40)]},
    )
    api.post(f"/sessions/{session_id}/end")

    assert api.get("/wellbeing").json()["days_with_data"] == 1
