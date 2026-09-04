from collections.abc import Mapping

import numpy as np

from app.schemas.emotion import CANONICAL_EMOTIONS, EmotionPrediction

LABEL_MAP = {
    "angry": "anger",
    "anger": "anger",
    "ang": "anger",
    "disgust": "disgust",
    "fear": "fear",
    "happy": "joy",
    "happiness": "joy",
    "hap": "joy",
    "joy": "joy",
    "neutral": "neutral",
    "neu": "neutral",
    "sad": "sadness",
    "sadness": "sadness",
    "surprise": "surprise",
    "surprised": "surprise",
}


def normalize_scores(native_scores: Mapping[str, float]) -> EmotionPrediction:
    """Map model-specific labels into the one vocabulary used by the API."""
    canonical_scores = {emotion: 0.0 for emotion in CANONICAL_EMOTIONS}
    for raw_label, score in native_scores.items():
        normalized_label = LABEL_MAP.get(raw_label.strip().lower())
        if normalized_label:
            canonical_scores[normalized_label] += max(float(score), 0.0)

    total = sum(canonical_scores.values())
    if total <= 0:
        raise ValueError("The model did not return usable emotion scores.")

    normalized = {label: value / total for label, value in canonical_scores.items()}
    label = max(normalized, key=normalized.get)
    return EmotionPrediction(label=label, confidence=normalized[label], scores=normalized)


def softmax_scores(logits: np.ndarray, id2label: Mapping[int | str, str]) -> EmotionPrediction:
    probabilities = np.exp(logits - np.max(logits))
    probabilities /= probabilities.sum()
    labels = {str(key): value for key, value in id2label.items()}
    native_scores = {
        labels.get(str(index), f"label_{index}"): float(score)
        for index, score in enumerate(probabilities)
    }
    return normalize_scores(native_scores)
