"""Late-fusion and cross-channel divergence — one engine, not two features.

The live session reports the text, voice and facial channels independently.
This module fuses them into a single labelled prediction while keeping every
channel's own scores visible, and lets the disagreement between channels
attenuate the fused confidence.

That coupling is the point. When the transcript reads joy at 0.9 and the voice
reads sadness at 0.8, a naive weighted average still produces a confident
label. Attenuating by divergence means the composite reports low confidence
instead, which is what makes the fused number honest.

A high divergence means the channels disagree. It does not mean the speaker is
concealing an emotion, and nothing here is a diagnosis.
"""

from collections.abc import Mapping
from itertools import combinations

import numpy as np

from app.schemas.emotion import (
    CANONICAL_EMOTIONS,
    ConflictAnalysis,
    FusedPrediction,
    FusionAnalysis,
    PairDivergence,
)

MINIMUM_CHANNELS_FOR_CONFLICT = 2


def to_vector(scores: Mapping[str, float]) -> np.ndarray:
    """Order a score mapping onto the canonical emotion axis and renormalize."""
    vector = np.array(
        [max(float(scores.get(emotion, 0.0)), 0.0) for emotion in CANONICAL_EMOTIONS],
        dtype=float,
    )
    total = vector.sum()
    if total <= 0:
        raise ValueError("Channel scores must contain at least one positive value.")
    return vector / total


def _kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """Base-2 KL divergence, treating 0 * log(0) as 0."""
    support = p > 0
    return float(np.sum(p[support] * np.log2(p[support] / q[support])))


def jensen_shannon_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """Symmetric divergence bounded to [0, 1] by the base-2 logarithm.

    The mixture m is positive wherever either input is, so the two KL terms are
    always finite. Bounded output is what makes a single threshold meaningful
    and what lets the value be used directly as an attenuation factor.
    """
    m = (p + q) / 2.0
    divergence = 0.5 * _kl_divergence(p, m) + 0.5 * _kl_divergence(q, m)
    return float(min(max(divergence, 0.0), 1.0))


def cosine_distance(p: np.ndarray, q: np.ndarray) -> float:
    """Baseline measure reported alongside the divergence for comparison."""
    norm = float(np.linalg.norm(p) * np.linalg.norm(q))
    if norm <= 0:
        raise ValueError("Channel scores must contain at least one positive value.")
    similarity = float(np.dot(p, q)) / norm
    return float(min(max(1.0 - similarity, 0.0), 1.0))


def resolve_weights(available: Mapping[str, np.ndarray], configured: Mapping[str, float]) -> dict[str, float]:
    """Restrict the configured weights to the channels present and renormalize.

    A missing channel must not silently shrink the fused distribution, so the
    remaining weights are rescaled to sum to one.
    """
    weights = {name: max(float(configured.get(name, 0.0)), 0.0) for name in available}
    total = sum(weights.values())
    if total <= 0:
        # Never leave the fusion undefined because the weights were misconfigured.
        return {name: 1.0 / len(available) for name in available}
    return {name: weight / total for name, weight in weights.items()}


def attenuation_for(divergence: float | None) -> float:
    """Map channel disagreement onto a confidence multiplier in [0, 1].

    Linear in the divergence: agreeing channels pass their confidence through
    unchanged, maximally disagreeing channels drive it to zero. Chosen for being
    bounded and explainable rather than tuned — revisit once the divergence
    distribution is known from labelled data.
    """
    if divergence is None:
        return 1.0
    return float(min(max(1.0 - divergence, 0.0), 1.0))


def fuse(
    available: Mapping[str, np.ndarray],
    weights: Mapping[str, float],
    attenuation: float,
) -> FusedPrediction:
    """Weighted late fusion of the channel distributions."""
    stacked = np.zeros(len(CANONICAL_EMOTIONS), dtype=float)
    for name, vector in available.items():
        stacked += weights[name] * vector
    total = stacked.sum()
    if total <= 0:
        raise ValueError("Fusion produced an empty distribution.")
    stacked /= total

    index = int(np.argmax(stacked))
    label = CANONICAL_EMOTIONS[index]
    raw_confidence = float(stacked[index])

    return FusedPrediction(
        label=label,
        confidence=float(raw_confidence * attenuation),
        raw_confidence=raw_confidence,
        attenuation=attenuation,
        scores={emotion: float(score) for emotion, score in zip(CANONICAL_EMOTIONS, stacked, strict=True)},
        weights=dict(weights),
    )


def measure_conflict(available: Mapping[str, np.ndarray], threshold: float) -> ConflictAnalysis:
    """Compare every available pair of channels and flag the widest disagreement.

    Fewer than two channels cannot disagree, so the analysis reports
    `insufficient_channels` rather than a misleading zero.
    """
    if len(available) < MINIMUM_CHANNELS_FOR_CONFLICT:
        return ConflictAnalysis(
            status="insufficient_channels",
            channels_compared=sorted(available),
            pairs=[],
            max_divergence=None,
            mean_divergence=None,
            most_divergent_pair=None,
            threshold=threshold,
            conflict_detected=False,
        )

    pairs = [
        PairDivergence(
            channels=[first, second],
            jensen_shannon=jensen_shannon_divergence(available[first], available[second]),
            cosine_distance=cosine_distance(available[first], available[second]),
        )
        for first, second in combinations(sorted(available), 2)
    ]

    divergences = [pair.jensen_shannon for pair in pairs]
    widest = max(pairs, key=lambda pair: pair.jensen_shannon)

    return ConflictAnalysis(
        status="conflict" if widest.jensen_shannon >= threshold else "aligned",
        channels_compared=sorted(available),
        pairs=pairs,
        max_divergence=widest.jensen_shannon,
        mean_divergence=float(sum(divergences) / len(divergences)),
        most_divergent_pair=widest.channels,
        threshold=threshold,
        conflict_detected=widest.jensen_shannon >= threshold,
    )


def analyze(
    channels: Mapping[str, Mapping[str, float] | None],
    threshold: float,
    weights: Mapping[str, float],
) -> FusionAnalysis:
    """Fuse the channels and measure their disagreement in a single pass."""
    available = {name: to_vector(scores) for name, scores in channels.items() if scores}

    conflict = measure_conflict(available, threshold)

    if not available:
        return FusionAnalysis(fused=None, channels={}, conflict=conflict)

    resolved = resolve_weights(available, weights)
    fused = fuse(available, resolved, attenuation_for(conflict.max_divergence))

    # Echo each channel back so the interface can always show the components
    # beside the fused headline rather than a bare number.
    echoed = {
        name: {emotion: float(score) for emotion, score in zip(CANONICAL_EMOTIONS, vector, strict=True)}
        for name, vector in available.items()
    }
    return FusionAnalysis(fused=fused, channels=echoed, conflict=conflict)
