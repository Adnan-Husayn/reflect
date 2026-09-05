from pydantic import BaseModel, Field, field_validator

CANONICAL_EMOTIONS = (
    "anger",
    "disgust",
    "fear",
    "joy",
    "neutral",
    "sadness",
    "surprise",
)

CHANNELS = ("text", "voice", "face")


class TextPredictionRequest(BaseModel):
    text: str = Field(max_length=5000)


class EmotionPrediction(BaseModel):
    label: str
    confidence: float
    scores: dict[str, float]


class LiveAudioAnalysis(BaseModel):
    transcript: str
    audio_prediction: EmotionPrediction | None
    text_prediction: EmotionPrediction | None


class HealthResponse(BaseModel):
    status: str
    models: dict[str, bool]


class ConflictRequest(BaseModel):
    """Latest score vector per channel. Any two channels are enough to compare."""

    text: dict[str, float] | None = None
    voice: dict[str, float] | None = None
    face: dict[str, float] | None = None

    @field_validator("text", "voice", "face")
    @classmethod
    def validate_channel_scores(cls, scores: dict[str, float] | None) -> dict[str, float] | None:
        if scores is None:
            return None
        unknown = set(scores) - set(CANONICAL_EMOTIONS)
        if unknown:
            raise ValueError(f"Unknown emotion labels: {', '.join(sorted(unknown))}.")
        if any(value < 0 for value in scores.values()):
            raise ValueError("Emotion scores cannot be negative.")
        if sum(scores.values()) <= 0:
            raise ValueError("Emotion scores must contain at least one positive value.")
        return scores

    def channels(self) -> dict[str, dict[str, float]]:
        present = {"text": self.text, "voice": self.voice, "face": self.face}
        return {name: scores for name, scores in present.items() if scores is not None}


class FusedPrediction(BaseModel):
    """The composite reading. `confidence` is the value to display."""

    label: str
    confidence: float
    raw_confidence: float
    attenuation: float
    scores: dict[str, float]
    weights: dict[str, float]


class PairDivergence(BaseModel):
    channels: list[str]
    jensen_shannon: float
    cosine_distance: float


class ConflictAnalysis(BaseModel):
    """Divergence between channels. Never a claim about a person's inner state."""

    status: str
    channels_compared: list[str]
    pairs: list[PairDivergence]
    max_divergence: float | None
    mean_divergence: float | None
    most_divergent_pair: list[str] | None
    threshold: float
    conflict_detected: bool


class FusionAnalysis(BaseModel):
    """Fused headline plus the per-channel components it was built from."""

    fused: FusedPrediction | None
    channels: dict[str, dict[str, float]]
    conflict: ConflictAnalysis
