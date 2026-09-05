import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.emotion import CANONICAL_EMOTIONS
from app.utils.fusion import (
    analyze,
    attenuation_for,
    cosine_distance,
    jensen_shannon_divergence,
    resolve_weights,
    to_vector,
)

THRESHOLD = 0.35
EQUAL_WEIGHTS = {"text": 1.0, "voice": 1.0, "face": 1.0}


def scores(**weights: float) -> dict[str, float]:
    """Build a full canonical score mapping from the named emotions only."""
    return {emotion: float(weights.get(emotion, 0.0)) for emotion in CANONICAL_EMOTIONS}


# ── divergence measures ───────────────────────────────────────────────


def test_identical_distributions_have_zero_divergence():
    vector = to_vector(scores(joy=0.7, neutral=0.3))
    assert jensen_shannon_divergence(vector, vector) == pytest.approx(0.0, abs=1e-12)
    assert cosine_distance(vector, vector) == pytest.approx(0.0, abs=1e-12)


def test_disjoint_distributions_reach_the_upper_bound():
    joy = to_vector(scores(joy=1.0))
    sadness = to_vector(scores(sadness=1.0))
    assert jensen_shannon_divergence(joy, sadness) == pytest.approx(1.0)
    assert cosine_distance(joy, sadness) == pytest.approx(1.0)


def test_divergence_is_symmetric():
    first = to_vector(scores(joy=0.6, surprise=0.4))
    second = to_vector(scores(sadness=0.5, fear=0.5))
    assert jensen_shannon_divergence(first, second) == pytest.approx(jensen_shannon_divergence(second, first))


def test_divergence_stays_within_bounds_across_random_pairs():
    generator = np.random.default_rng(0)
    for _ in range(200):
        first = to_vector(dict(zip(CANONICAL_EMOTIONS, generator.random(7), strict=True)))
        second = to_vector(dict(zip(CANONICAL_EMOTIONS, generator.random(7), strict=True)))
        assert 0.0 <= jensen_shannon_divergence(first, second) <= 1.0


def test_unnormalised_scores_are_renormalised():
    """A client sending raw weights must match one sending probabilities."""
    doubled = to_vector(scores(joy=1.4, neutral=0.6))
    normalised = to_vector(scores(joy=0.7, neutral=0.3))
    assert np.allclose(doubled, normalised)


def test_all_zero_scores_are_rejected():
    with pytest.raises(ValueError):
        to_vector(scores())


# ── attenuation ───────────────────────────────────────────────────────


def test_agreement_passes_confidence_through_unchanged():
    assert attenuation_for(0.0) == pytest.approx(1.0)


def test_total_disagreement_drives_confidence_to_zero():
    assert attenuation_for(1.0) == pytest.approx(0.0)


def test_a_lone_channel_is_not_penalised():
    """With nothing to disagree with, there is no reason to attenuate."""
    assert attenuation_for(None) == pytest.approx(1.0)


# ── weights ───────────────────────────────────────────────────────────


def test_weights_renormalise_over_the_channels_present():
    available = {"text": to_vector(scores(joy=1.0)), "voice": to_vector(scores(joy=1.0))}
    resolved = resolve_weights(available, EQUAL_WEIGHTS)
    assert set(resolved) == {"text", "voice"}
    assert sum(resolved.values()) == pytest.approx(1.0)


def test_misconfigured_zero_weights_fall_back_to_equal():
    available = {"text": to_vector(scores(joy=1.0)), "voice": to_vector(scores(joy=1.0))}
    resolved = resolve_weights(available, {"text": 0.0, "voice": 0.0, "face": 0.0})
    assert resolved == {"text": pytest.approx(0.5), "voice": pytest.approx(0.5)}


# ── fusion ────────────────────────────────────────────────────────────


def test_agreeing_channels_fuse_to_a_confident_label():
    result = analyze(
        {
            "text": scores(joy=0.8, neutral=0.2),
            "voice": scores(joy=0.75, neutral=0.25),
            "face": scores(joy=0.85, neutral=0.15),
        },
        THRESHOLD,
        EQUAL_WEIGHTS,
    )
    assert result.conflict.status == "aligned"
    assert result.fused.label == "joy"
    assert result.fused.attenuation > 0.95
    assert result.fused.confidence == pytest.approx(result.fused.raw_confidence, rel=0.05)


def test_disagreeing_channels_must_not_produce_a_confident_label():
    """The locked design decision: divergence attenuates the fused confidence."""
    result = analyze(
        {
            "text": scores(joy=0.9, neutral=0.1),
            "voice": scores(sadness=0.8, neutral=0.2),
            "face": scores(sadness=0.85, neutral=0.15),
        },
        THRESHOLD,
        EQUAL_WEIGHTS,
    )
    assert result.conflict.conflict_detected is True
    assert result.fused.confidence < result.fused.raw_confidence / 2
    assert result.fused.attenuation < 0.5


def test_fused_distribution_stays_normalised():
    result = analyze(
        {"text": scores(joy=0.6, neutral=0.4), "voice": scores(fear=0.5, anger=0.5)},
        THRESHOLD,
        EQUAL_WEIGHTS,
    )
    assert sum(result.fused.scores.values()) == pytest.approx(1.0)


def test_channels_are_echoed_back_so_components_stay_visible():
    """Fused headline plus the individual scores — never a bare number."""
    result = analyze({"text": scores(joy=1.0), "voice": scores(sadness=1.0)}, THRESHOLD, EQUAL_WEIGHTS)
    assert set(result.channels) == {"text", "voice"}
    assert result.channels["text"]["joy"] == pytest.approx(1.0)
    assert result.channels["voice"]["sadness"] == pytest.approx(1.0)


def test_weighting_shifts_the_fused_label_toward_the_trusted_channel():
    channels = {"text": scores(joy=1.0), "voice": scores(sadness=1.0)}
    trusting_voice = analyze(channels, THRESHOLD, {"text": 0.1, "voice": 0.9, "face": 0.0})
    trusting_text = analyze(channels, THRESHOLD, {"text": 0.9, "voice": 0.1, "face": 0.0})
    assert trusting_voice.fused.label == "sadness"
    assert trusting_text.fused.label == "joy"


def test_a_single_channel_fuses_to_itself_without_conflict():
    result = analyze({"text": scores(joy=0.7, neutral=0.3)}, THRESHOLD, EQUAL_WEIGHTS)
    assert result.conflict.status == "insufficient_channels"
    assert result.fused.label == "joy"
    assert result.fused.attenuation == pytest.approx(1.0)
    assert result.fused.confidence == pytest.approx(result.fused.raw_confidence)


def test_an_unavailable_channel_is_skipped_without_disabling_fusion():
    result = analyze(
        {"text": scores(joy=1.0), "voice": scores(sadness=1.0), "face": None},
        THRESHOLD,
        EQUAL_WEIGHTS,
    )
    assert result.conflict.channels_compared == ["text", "voice"]
    assert set(result.fused.weights) == {"text", "voice"}
    assert sum(result.fused.weights.values()) == pytest.approx(1.0)


def test_no_channels_yields_no_fusion_rather_than_an_empty_distribution():
    result = analyze({}, THRESHOLD, EQUAL_WEIGHTS)
    assert result.fused is None
    assert result.channels == {}
    assert result.conflict.status == "insufficient_channels"


def test_pairs_cover_every_combination_exactly_once():
    channels = dict.fromkeys(("text", "voice", "face"), scores(joy=1.0))
    result = analyze(channels, THRESHOLD, EQUAL_WEIGHTS)
    compared = {tuple(pair.channels) for pair in result.conflict.pairs}
    assert compared == {("face", "text"), ("face", "voice"), ("text", "voice")}


# ── endpoint ──────────────────────────────────────────────────────────


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    """The fusion endpoint needs no models; keep the real ones unloaded."""
    monkeypatch.setattr(
        "app.main.load_models",
        lambda: {"text": None, "audio": None, "facial": None, "speech": None},
    )
    with TestClient(app) as test_client:
        yield test_client


def test_endpoint_returns_fusion_channels_and_conflict(client: TestClient):
    response = client.post(
        "/analyze/fusion",
        json={"text": scores(joy=0.9, neutral=0.1), "voice": scores(sadness=0.9, neutral=0.1)},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"fused", "channels", "conflict"}
    assert set(body["fused"]) == {
        "label",
        "confidence",
        "raw_confidence",
        "attenuation",
        "scores",
        "weights",
    }
    assert body["conflict"]["conflict_detected"] is True
    assert body["fused"]["confidence"] < body["fused"]["raw_confidence"]
    assert set(body["channels"]) == {"text", "voice"}


def test_endpoint_handles_a_single_channel(client: TestClient):
    response = client.post("/analyze/fusion", json={"text": scores(joy=1.0)})
    assert response.status_code == 200
    body = response.json()
    assert body["conflict"]["status"] == "insufficient_channels"
    assert body["fused"]["label"] == "joy"


def test_endpoint_rejects_unknown_emotion_labels(client: TestClient):
    response = client.post("/analyze/fusion", json={"text": {"elation": 1.0}})
    assert response.status_code == 422


def test_endpoint_rejects_negative_scores(client: TestClient):
    response = client.post("/analyze/fusion", json={"text": scores(joy=1.0) | {"fear": -0.5}})
    assert response.status_code == 422


def test_endpoint_rejects_an_all_zero_channel(client: TestClient):
    response = client.post("/analyze/fusion", json={"text": scores(), "voice": scores(joy=1.0)})
    assert response.status_code == 422
