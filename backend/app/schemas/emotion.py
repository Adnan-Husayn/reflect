from pydantic import BaseModel, Field

CANONICAL_EMOTIONS = (
    "anger",
    "disgust",
    "fear",
    "joy",
    "neutral",
    "sadness",
    "surprise",
)


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
