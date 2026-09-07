import pytest
from fastapi.testclient import TestClient

from app.instruments import INSTRUMENTS
from app.instruments.phq8 import PHQ8, score_responses

COMPLETE = {f"q{index}": 1 for index in range(1, 9)}

# Anything that reads as a clinical interpretation of a total. The app scores
# the instrument and plots the number; it never renders a verdict.
SEVERITY_WORDS = ("mild", "moderate", "moderately severe", "severe", "minimal", "cutoff", "cut-off")


# ── the instrument ────────────────────────────────────────────────────


def test_phq8_has_eight_items_scored_zero_to_three():
    assert len(PHQ8.items) == 8
    assert PHQ8.allowed_values == {0, 1, 2, 3}
    assert PHQ8.max_score == 24


def test_the_self_harm_item_is_absent():
    """PHQ-8 is PHQ-9 without item 9, which asks about thoughts of self-harm.

    Collecting it would create a duty of response this project cannot meet.
    """
    joined = " ".join(item.text.lower() for item in PHQ8.items)
    for phrase in ("dead", "hurting yourself", "better off dead", "self-harm", "suicide"):
        assert phrase not in joined


def test_no_severity_band_appears_in_the_definition():
    joined = " ".join([PHQ8.name, PHQ8.prompt, *(item.text for item in PHQ8.items)]).lower()
    for word in SEVERITY_WORDS:
        assert word not in joined


def test_only_instruments_with_a_server_side_definition_are_accepted():
    """An instrument the server cannot score would leave the client's number
    unchecked, which is the hole this package closes."""
    assert set(INSTRUMENTS) == {"PHQ-8", "GAD-7"}


def test_an_undefined_instrument_is_still_rejected():
    assert "PHQ-9" not in INSTRUMENTS
    assert "BDI" not in INSTRUMENTS


# ── scoring ───────────────────────────────────────────────────────────


def test_the_total_is_the_sum_of_the_items():
    assert score_responses(PHQ8, COMPLETE) == 8
    assert score_responses(PHQ8, dict.fromkeys(COMPLETE, 0)) == 0
    assert score_responses(PHQ8, dict.fromkeys(COMPLETE, 3)) == 24


def test_a_partial_submission_is_rejected_rather_than_scored_as_zero():
    """Treating an absent answer as zero would bias every score downward."""
    with pytest.raises(ValueError, match="Missing responses"):
        score_responses(PHQ8, {"q1": 1, "q2": 2})


def test_an_unknown_item_is_rejected():
    with pytest.raises(ValueError, match="Unknown items"):
        score_responses(PHQ8, COMPLETE | {"q9": 3})


@pytest.mark.parametrize("value", [-1, 4, 99])
def test_an_out_of_range_value_is_rejected(value: int):
    with pytest.raises(ValueError, match="Responses must be one of"):
        score_responses(PHQ8, COMPLETE | {"q1": value})


# ── endpoint ──────────────────────────────────────────────────────────


def test_the_instrument_is_served_for_the_form_to_render_from(api: TestClient):
    body = api.get("/instruments/PHQ-8").json()
    assert body["code"] == "PHQ-8"
    assert len(body["items"]) == 8
    assert [option["value"] for option in body["options"]] == [0, 1, 2, 3]
    assert body["options"][0]["label"] == "Not at all"
    assert body["max_score"] == 24


def test_the_served_definition_carries_no_severity_bands(api: TestClient):
    body = api.get("/instruments/PHQ-8").text.lower()
    for word in SEVERITY_WORDS:
        assert word not in body


def test_an_unknown_instrument_is_a_404(api: TestClient):
    assert api.get("/instruments/PHQ-9").status_code == 404


# ── submission validation ─────────────────────────────────────────────


def checkin(responses: dict, score: int, instrument: str = "PHQ-8") -> dict:
    return {
        "taken_on": "2026-09-06",
        "instrument": instrument,
        "responses": responses,
        "score": score,
    }


def test_a_valid_submission_is_stored(api: TestClient):
    response = api.post("/checkins", json=checkin(COMPLETE, 8))
    assert response.status_code == 201
    assert response.json()["score"] == 8


def test_a_score_disagreeing_with_its_responses_is_rejected(api: TestClient):
    """Previously a PHQ-8 with two answers and a score of 9999 was valid."""
    response = api.post("/checkins", json=checkin(COMPLETE, 9999))
    assert response.status_code == 422
    assert "does not match the responses" in response.text


def test_a_submission_missing_items_is_rejected(api: TestClient):
    assert api.post("/checkins", json=checkin({"q1": 1, "q2": 1}, 2)).status_code == 422


def test_an_out_of_range_item_is_rejected(api: TestClient):
    assert api.post("/checkins", json=checkin(COMPLETE | {"q1": 7}, 14)).status_code == 422


def test_an_undefined_instrument_is_rejected(api: TestClient):
    assert api.post("/checkins", json=checkin(COMPLETE, 8, "PHQ-9")).status_code == 422


def test_gad7_is_scored_by_its_own_seven_items(api: TestClient):
    """Eight PHQ-8 answers are not a valid GAD-7 submission."""
    assert api.post("/checkins", json=checkin(COMPLETE, 8, "GAD-7")).status_code == 422

    seven = {f"q{index}": 1 for index in range(1, 8)}
    response = api.post("/checkins", json=checkin(seven, 7, "GAD-7"))
    assert response.status_code == 201
    assert response.json()["score"] == 7


def test_both_instruments_can_be_answered_on_the_same_day(api: TestClient):
    """The uniqueness constraint is per instrument, not per day."""
    seven = {f"q{index}": 1 for index in range(1, 8)}
    assert api.post("/checkins", json=checkin(COMPLETE, 8, "PHQ-8")).status_code == 201
    assert api.post("/checkins", json=checkin(seven, 7, "GAD-7")).status_code == 201


def test_gad7_carries_no_severity_bands(api: TestClient):
    body = api.get("/instruments/GAD-7").text.lower()
    for word in SEVERITY_WORDS:
        assert word not in body
