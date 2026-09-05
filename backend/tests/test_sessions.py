from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.schemas.emotion import CANONICAL_EMOTIONS

START = datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC)


def scores(**weights: float) -> dict[str, float]:
    return {emotion: float(weights.get(emotion, 0.0)) for emotion in CANONICAL_EMOTIONS}


def reading(offset: int, channel: str, label: str, **weights: float) -> dict:
    return {
        "t": (START + timedelta(seconds=offset)).isoformat(),
        "channel": channel,
        "label": label,
        "confidence": 0.8,
        "scores": scores(**weights),
    }


def fused(offset: int, label: str, conflict: bool = False, **weights: float) -> dict:
    return {
        "t": (START + timedelta(seconds=offset)).isoformat(),
        "label": label,
        "confidence": 0.4,
        "raw_confidence": 0.8,
        "attenuation": 0.5,
        "max_divergence": 0.5,
        "conflict": conflict,
        "scores": scores(**weights),
    }


def open_session(api: TestClient) -> str:
    response = api.post("/sessions")
    assert response.status_code == 201
    return response.json()["id"]


# ── lifecycle ─────────────────────────────────────────────────────────


def test_open_session_returns_an_id_and_no_end_time(api: TestClient):
    body = api.post("/sessions").json()
    assert body["id"]
    assert body["ended_at"] is None


def test_readings_are_appended_in_batches(api: TestClient):
    session_id = open_session(api)
    response = api.post(
        f"/sessions/{session_id}/readings",
        json={
            "readings": [reading(0, "face", "joy", joy=1.0), reading(2, "voice", "joy", joy=1.0)],
            "fused": [fused(2, "joy", joy=1.0)],
        },
    )
    assert response.status_code == 200
    assert response.json()["readings_added"] == 2
    assert response.json()["fused_added"] == 1


def test_session_survives_and_returns_its_readings(api: TestClient):
    session_id = open_session(api)
    api.post(
        f"/sessions/{session_id}/readings",
        json={"readings": [reading(0, "text", "joy", joy=1.0)], "fused": [fused(0, "joy", joy=1.0)]},
    )
    body = api.get(f"/sessions/{session_id}").json()
    assert len(body["readings"]) == 1
    assert len(body["fused_readings"]) == 1
    assert body["readings"][0]["channel"] == "text"


def test_sessions_are_listed_newest_first(api: TestClient):
    first = open_session(api)
    second = open_session(api)
    listed = [item["id"] for item in api.get("/sessions").json()]
    assert set(listed) == {first, second}


# ── state transitions ─────────────────────────────────────────────────


def test_readings_are_refused_after_the_session_ends(api: TestClient):
    session_id = open_session(api)
    api.post(f"/sessions/{session_id}/end")
    response = api.post(
        f"/sessions/{session_id}/readings",
        json={"readings": [reading(0, "face", "joy", joy=1.0)], "fused": []},
    )
    assert response.status_code == 409


def test_ending_twice_is_refused(api: TestClient):
    session_id = open_session(api)
    assert api.post(f"/sessions/{session_id}/end").status_code == 200
    assert api.post(f"/sessions/{session_id}/end").status_code == 409


def test_unknown_session_is_a_404(api: TestClient):
    assert api.get("/sessions/does-not-exist").status_code == 404
    assert api.post("/sessions/does-not-exist/end").status_code == 404


# ── rollup ────────────────────────────────────────────────────────────


def test_summary_valence_reads_fused_readings_only(api: TestClient):
    """Face samples every 2s against audio's 5s. If the rollup averaged
    per-channel readings, the facial channel would dominate the mean by
    sampling rate alone — so the summary must ignore them for valence."""
    session_id = open_session(api)
    api.post(
        f"/sessions/{session_id}/readings",
        json={
            # Eight sad facial readings would drag a per-channel mean negative.
            "readings": [reading(offset, "face", "sadness", sadness=1.0) for offset in range(0, 16, 2)],
            # The fused truth is joy.
            "fused": [fused(offset, "joy", joy=1.0) for offset in (5, 10)],
        },
    )
    summary = api.post(f"/sessions/{session_id}/end").json()
    assert summary["n_readings"] == 8
    assert summary["n_fused_readings"] == 2
    assert summary["mean_valence"] == 1.0
    assert summary["dominant_label"] == "joy"


def test_conflict_rate_is_the_proportion_of_flagged_fused_readings(api: TestClient):
    session_id = open_session(api)
    api.post(
        f"/sessions/{session_id}/readings",
        json={
            "readings": [],
            "fused": [
                fused(0, "joy", conflict=True, joy=1.0),
                fused(5, "joy", conflict=False, joy=1.0),
                fused(10, "joy", conflict=False, joy=1.0),
                fused(15, "joy", conflict=True, joy=1.0),
            ],
        },
    )
    assert api.post(f"/sessions/{session_id}/end").json()["conflict_rate"] == 0.5


def test_channel_counts_reveal_an_unavailable_channel(api: TestClient):
    """A denied camera shows as no face readings at all."""
    session_id = open_session(api)
    api.post(
        f"/sessions/{session_id}/readings",
        json={
            "readings": [reading(0, "voice", "joy", joy=1.0), reading(5, "text", "joy", joy=1.0)],
            "fused": [],
        },
    )
    counts = api.post(f"/sessions/{session_id}/end").json()["channel_counts"]
    assert counts == {"voice": 1, "text": 1}
    assert "face" not in counts


def test_empty_session_summarises_without_inventing_a_mood(api: TestClient):
    session_id = open_session(api)
    summary = api.post(f"/sessions/{session_id}/end").json()
    assert summary["mean_valence"] is None
    assert summary["conflict_rate"] is None
    assert summary["dominant_label"] is None


# ── validation ────────────────────────────────────────────────────────


def test_unknown_channel_is_rejected(api: TestClient):
    session_id = open_session(api)
    payload = {"readings": [reading(0, "eeg", "joy", joy=1.0)], "fused": []}
    assert api.post(f"/sessions/{session_id}/readings", json=payload).status_code == 422


def test_unknown_label_is_rejected(api: TestClient):
    session_id = open_session(api)
    payload = {"readings": [reading(0, "face", "elation", joy=1.0)], "fused": []}
    assert api.post(f"/sessions/{session_id}/readings", json=payload).status_code == 422


# ── deletion ──────────────────────────────────────────────────────────


def test_deleting_a_session_removes_its_readings(api: TestClient):
    session_id = open_session(api)
    api.post(
        f"/sessions/{session_id}/readings",
        json={
            "readings": [reading(0, "face", "joy", joy=1.0), reading(2, "voice", "joy", joy=1.0)],
            "fused": [fused(2, "joy", joy=1.0)],
        },
    )
    receipt = api.delete(f"/sessions/{session_id}").json()
    assert receipt == {
        "deleted_sessions": 1,
        "deleted_readings": 2,
        "deleted_fused_readings": 1,
        "deleted_checkins": 0,
    }
    assert api.get(f"/sessions/{session_id}").status_code == 404


def test_withdrawal_erases_every_session_and_checkin(api: TestClient):
    first = open_session(api)
    api.post(
        f"/sessions/{first}/readings",
        json={"readings": [reading(0, "face", "joy", joy=1.0)], "fused": [fused(0, "joy", joy=1.0)]},
    )
    open_session(api)
    api.post(
        "/checkins",
        json={"taken_on": "2026-09-05", "instrument": "PHQ-8", "responses": {"q1": 2}, "score": 2},
    )

    receipt = api.delete("/users/me/data").json()
    assert receipt["deleted_sessions"] == 2
    assert receipt["deleted_readings"] == 1
    assert receipt["deleted_fused_readings"] == 1
    assert receipt["deleted_checkins"] == 1

    assert api.get("/sessions").json() == []
    assert api.get("/checkins").json() == []


def test_deleting_an_unknown_session_is_a_404(api: TestClient):
    assert api.delete("/sessions/does-not-exist").status_code == 404


# ── check-ins ─────────────────────────────────────────────────────────


def test_checkin_is_recorded_and_listed(api: TestClient):
    payload = {
        "taken_on": "2026-09-05",
        "instrument": "PHQ-8",
        "responses": {"q1": 1, "q2": 3},
        "score": 4,
    }
    assert api.post("/checkins", json=payload).status_code == 201
    listed = api.get("/checkins").json()
    assert len(listed) == 1
    assert listed[0]["instrument"] == "PHQ-8"
    assert listed[0]["score"] == 4


def test_one_checkin_per_instrument_per_day(api: TestClient):
    payload = {
        "taken_on": "2026-09-05",
        "instrument": "PHQ-8",
        "responses": {"q1": 1},
        "score": 1,
    }
    assert api.post("/checkins", json=payload).status_code == 201
    assert api.post("/checkins", json=payload).status_code == 409


def test_phq9_is_refused_because_phq8_is_the_chosen_instrument(api: TestClient):
    """PHQ-8 drops the suicidality item; accepting PHQ-9 would pull in a
    risk-management burden the project is explicitly not equipped for."""
    payload = {
        "taken_on": "2026-09-05",
        "instrument": "PHQ-9",
        "responses": {"q1": 1},
        "score": 1,
    }
    assert api.post("/checkins", json=payload).status_code == 422
