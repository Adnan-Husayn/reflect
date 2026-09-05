"""The no-raw-media guarantee.

The README claims audio, frames and transcripts are never stored. These tests
exist so that claim cannot quietly become false — the realistic failure is not
an attacker, it is a teammate adding a field in good faith and nobody noticing.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, LargeBinary, String, Text

from app.db.models import Base
from app.schemas.emotion import CANONICAL_EMOTIONS

FORBIDDEN_NAMES = {"audio", "image", "frame", "media", "transcript", "waveform", "blob", "bytes"}
START = datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC)


def scores(**weights: float) -> dict[str, float]:
    return {emotion: float(weights.get(emotion, 0.0)) for emotion in CANONICAL_EMOTIONS}


def test_no_binary_column_exists_anywhere():
    """Structural, not procedural: with no bytes-typed column, the schema
    cannot hold media regardless of what a caller sends."""
    offenders = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, LargeBinary)
    ]
    assert offenders == [], f"binary columns present: {offenders}"


def test_no_column_is_named_after_media_or_a_transcript():
    offenders = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if any(word in column.name.lower() for word in FORBIDDEN_NAMES)
    ]
    assert offenders == [], f"media-shaped columns present: {offenders}"


def test_free_text_columns_are_length_capped():
    """An unbounded text column is where a transcript would eventually land."""
    offenders = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, Text) or (isinstance(column.type, String) and column.type.length is None)
    ]
    assert offenders == [], f"unbounded text columns present: {offenders}"


def test_json_columns_are_confined_to_score_and_response_payloads():
    allowed = {
        ("readings", "scores"),
        ("fused_readings", "scores"),
        ("session_summaries", "channel_counts"),
        ("checkins", "responses"),
    }
    actual = {
        (table.name, column.name)
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, JSON)
    }
    assert actual == allowed, f"unexpected JSON columns: {actual - allowed}"


@pytest.mark.parametrize("smuggled", ["transcript", "audio", "frame"])
def test_extra_fields_are_rejected_rather_than_ignored(api: TestClient, smuggled: str):
    """The load-bearing guard. Without extra='forbid' this would be accepted
    and silently dropped today, then persisted the moment a matching column
    appeared."""
    session_id = api.post("/sessions").json()["id"]
    response = api.post(
        f"/sessions/{session_id}/readings",
        json={
            "readings": [
                {
                    "t": START.isoformat(),
                    "channel": "voice",
                    "label": "joy",
                    "confidence": 0.9,
                    "scores": scores(joy=1.0),
                    smuggled: "I said something private",
                }
            ],
            "fused": [],
        },
    )
    assert response.status_code == 422


def test_the_persistence_api_exposes_no_multipart_endpoint():
    """Media can only arrive as multipart; there is nowhere to send it."""
    from app.main import app

    session_routes = [
        route
        for route in app.routes
        if getattr(route, "path", "").startswith(("/sessions", "/checkins", "/users"))
    ]
    assert session_routes, "expected the persistence routes to be registered"

    schema = app.openapi()
    for route in session_routes:
        for method in {method.lower() for method in getattr(route, "methods", set())}:
            operation = schema["paths"].get(route.path, {}).get(method)
            if operation is None:
                continue
            content = operation.get("requestBody", {}).get("content", {})
            assert "multipart/form-data" not in content, f"{method.upper()} {route.path}"
