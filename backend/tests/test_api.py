from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.schemas.emotion import CANONICAL_EMOTIONS, EmotionPrediction


class FakeTextModel:
    def predict(self, text: str) -> EmotionPrediction:
        assert text
        scores = {label: 0.0 for label in CANONICAL_EMOTIONS}
        scores["joy"] = 1.0
        return EmotionPrediction(label="joy", confidence=1.0, scores=scores)


class FakeAudioModel:
    def predict(self, waveform) -> EmotionPrediction:
        scores = {label: 0.0 for label in CANONICAL_EMOTIONS}
        scores["neutral"] = 1.0
        return EmotionPrediction(label="neutral", confidence=1.0, scores=scores)


class FakeSpeechModel:
    def transcribe(self, waveform) -> str:
        return "I am happy to be here."


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.main.load_models",
        lambda: {
            "text": FakeTextModel(),
            "audio": FakeAudioModel(),
            "facial": None,
            "speech": FakeSpeechModel(),
        },
    )
    with TestClient(app) as test_client:
        yield test_client


def test_empty_text_is_rejected(client: TestClient):
    response = client.post("/predict/text", json={"text": "   "})
    assert response.status_code == 400
    assert response.json()["detail"] == "Text input cannot be empty."


def test_valid_text_uses_common_response_shape(client: TestClient):
    response = client.post("/predict/text", json={"text": "I feel cheerful today."})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"label", "confidence", "scores"}
    assert set(body["scores"]) == set(CANONICAL_EMOTIONS)


def test_unsupported_audio_type_is_rejected(client: TestClient):
    response = client.post("/predict/audio", files={"file": ("note.txt", b"not audio", "text/plain")})
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported audio format."


def test_malformed_image_is_rejected(client: TestClient):
    response = client.post("/predict/facial", files={"file": ("image.jpg", b"not an image", "image/jpeg")})
    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded image could not be processed."


def test_no_face_is_reported(client: TestClient):
    image = Image.new("RGB", (80, 80), color="white")
    data = BytesIO()
    image.save(data, format="JPEG")
    response = client.post("/predict/facial", files={"file": ("blank.jpg", data.getvalue(), "image/jpeg")})
    assert response.status_code == 400
    assert response.json()["detail"] == "No face was detected in the captured image."


def test_health_returns_model_status(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "models": {"text": True, "audio": True, "facial": False, "speech": True},
    }


def test_live_audio_returns_transcript_and_independent_predictions(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.routers.predictions.decode_audio", lambda _: [0.0, 0.1, 0.0])
    response = client.post(
        "/predict/live/audio",
        files={"file": ("segment.webm", b"audio-segment", "audio/webm")},
    )
    assert response.status_code == 200
    assert response.json() == {
        "transcript": "I am happy to be here.",
        "audio_prediction": {"label": "neutral", "confidence": 1.0, "scores": {label: 1.0 if label == "neutral" else 0.0 for label in CANONICAL_EMOTIONS}},
        "text_prediction": {"label": "joy", "confidence": 1.0, "scores": {label: 1.0 if label == "joy" else 0.0 for label in CANONICAL_EMOTIONS}},
    }
