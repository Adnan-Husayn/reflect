"""Valence scoring for session rollups.

Valence is computed across the whole score vector rather than the argmax label,
so a reading that is 0.5 sadness and 0.4 joy is not recorded as if it were
purely sad.
"""

from collections.abc import Mapping

from app.schemas.emotion import CANONICAL_EMOTIONS

# Surprise is genuinely ambiguous in valence — it accompanies both delight and
# alarm — so it sits at zero rather than being forced to a side. Named here so
# M5 can revisit it once the distress construct is defined, instead of the
# choice being buried in a comprehension.
AMBIGUOUS_VALENCE = 0.0

VALENCE: dict[str, float] = {
    "joy": 1.0,
    "anger": -1.0,
    "disgust": -1.0,
    "fear": -1.0,
    "sadness": -1.0,
    "neutral": 0.0,
    "surprise": AMBIGUOUS_VALENCE,
}

assert set(VALENCE) == set(CANONICAL_EMOTIONS), "valence map must cover every canonical emotion"


def valence_of(scores: Mapping[str, float]) -> float:
    """Expected valence of one score vector, in [-1, 1].

    The vector is renormalized first, so callers may pass raw weights.
    """
    total = sum(max(float(value), 0.0) for value in scores.values())
    if total <= 0:
        raise ValueError("Scores must contain at least one positive value.")
    return sum(
        VALENCE[emotion] * max(float(scores.get(emotion, 0.0)), 0.0) / total for emotion in CANONICAL_EMOTIONS
    )


def mean_valence(score_vectors: list[Mapping[str, float]]) -> float | None:
    """Mean valence across readings, or None when there is nothing to average.

    Callers must pass *fused* readings only. Averaging per-channel readings
    instead would let the facial channel dominate: it samples every 2 seconds
    against the audio channel's 5, so its readings outnumber them roughly 2.5
    to 1 and the mean would follow the sampling rate rather than the mood.
    """
    if not score_vectors:
        return None
    return sum(valence_of(vector) for vector in score_vectors) / len(score_vectors)
