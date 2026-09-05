import pytest

from app.schemas.emotion import CANONICAL_EMOTIONS
from app.utils.valence import VALENCE, mean_valence, valence_of


def scores(**weights: float) -> dict[str, float]:
    return {emotion: float(weights.get(emotion, 0.0)) for emotion in CANONICAL_EMOTIONS}


def test_valence_map_covers_every_canonical_emotion():
    assert set(VALENCE) == set(CANONICAL_EMOTIONS)


def test_pure_joy_and_pure_sadness_sit_at_the_bounds():
    assert valence_of(scores(joy=1.0)) == pytest.approx(1.0)
    assert valence_of(scores(sadness=1.0)) == pytest.approx(-1.0)


def test_neutral_and_surprise_are_zero_valence():
    assert valence_of(scores(neutral=1.0)) == pytest.approx(0.0)
    assert valence_of(scores(surprise=1.0)) == pytest.approx(0.0)


def test_valence_uses_the_whole_vector_not_the_argmax():
    """0.5 sadness against 0.4 joy is mildly negative, not fully sad."""
    mixed = valence_of(scores(sadness=0.5, joy=0.4, neutral=0.1))
    assert mixed == pytest.approx(-0.1)
    assert mixed > valence_of(scores(sadness=1.0))


def test_raw_weights_match_probabilities():
    assert valence_of(scores(joy=2.0, sadness=2.0)) == pytest.approx(valence_of(scores(joy=0.5, sadness=0.5)))


def test_all_zero_scores_are_rejected():
    with pytest.raises(ValueError):
        valence_of(scores())


def test_mean_valence_of_nothing_is_none_rather_than_zero():
    """An empty session has no valence; zero would read as neutral mood."""
    assert mean_valence([]) is None


def test_mean_valence_averages_across_readings():
    assert mean_valence([scores(joy=1.0), scores(sadness=1.0)]) == pytest.approx(0.0)
    assert mean_valence([scores(joy=1.0), scores(joy=1.0), scores(sadness=1.0)]) == pytest.approx(1 / 3)
