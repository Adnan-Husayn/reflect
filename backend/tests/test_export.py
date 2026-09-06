"""CSV export.

Exists so the report can be written from numbers rather than screenshots, and
so a participant can take their data with them.
"""

from fastapi.testclient import TestClient

from app.schemas.emotion import CANONICAL_EMOTIONS


def scores(**weights: float) -> dict[str, float]:
    return {emotion: float(weights.get(emotion, 0.0)) for emotion in CANONICAL_EMOTIONS}


def phq8(**answers: int) -> dict:
    responses = {f"q{index}": answers.get(f"q{index}", 0) for index in range(1, 9)}
    return {"responses": responses, "score": sum(responses.values())}


def recorded_session(api: TestClient) -> str:
    session_id = api.post("/sessions").json()["id"]
    api.post(
        f"/sessions/{session_id}/readings",
        json={
            "readings": [
                {
                    "t": "2026-09-06T12:00:00Z",
                    "channel": "face",
                    "label": "joy",
                    "confidence": 0.8,
                    "scores": scores(joy=1.0),
                }
            ],
            "fused": [
                {
                    "t": "2026-09-06T12:00:00Z",
                    "label": "joy",
                    "confidence": 0.7,
                    "raw_confidence": 0.8,
                    "attenuation": 0.9,
                    "max_divergence": 0.1,
                    "conflict": False,
                    "scores": scores(joy=1.0),
                }
            ],
        },
    )
    api.post(f"/sessions/{session_id}/end")
    return session_id


def test_sessions_export_has_a_header_and_a_row_per_session(api: TestClient):
    recorded_session(api)
    response = api.get("/export/sessions.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("session_id,started_at,ended_at")
    assert len(lines) == 2


def test_the_export_downloads_rather_than_rendering(api: TestClient):
    assert "attachment" in api.get("/export/sessions.csv").headers["content-disposition"]


def test_checkins_export_keeps_the_item_responses(api: TestClient):
    """Item-level answers allow rescoring and are what a methods section
    describes, so the total alone is not enough."""
    api.post("/checkins", json={"taken_on": "2026-09-06", "instrument": "PHQ-8", **phq8(q1=2, q3=1)})
    body = api.get("/export/checkins.csv").text

    assert "q1=2" in body
    assert "q3=1" in body
    assert "PHQ-8" in body


def test_an_empty_account_exports_a_header_and_nothing_else(api: TestClient):
    assert api.get("/export/sessions.csv").text.strip().count("\n") == 0


def test_no_raw_media_column_exists_in_either_export(api: TestClient):
    """There is nothing to export because nothing is stored."""
    for path in ("/export/sessions.csv", "/export/checkins.csv"):
        header = api.get(path).text.splitlines()[0].lower()
        for forbidden in ("transcript", "audio", "frame", "image", "media"):
            assert forbidden not in header


def test_the_export_requires_an_account(anon: TestClient):
    assert anon.get("/export/sessions.csv").status_code == 401
    assert anon.get("/export/checkins.csv").status_code == 401


def test_one_account_exports_none_of_anothers_data(api: TestClient):
    recorded_session(api)
    api.post("/auth/logout")
    api.cookies.clear()
    api.post("/auth/register", json={"email": "second@example.com", "password": "another-long-password"})

    assert api.get("/export/sessions.csv").text.strip().count("\n") == 0
