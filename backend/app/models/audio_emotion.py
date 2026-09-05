import numpy as np
import torch
from transformers import AutoModelForAudioClassification, Wav2Vec2FeatureExtractor

from app.schemas.emotion import EmotionPrediction
from app.utils.emotions import softmax_scores

MODEL_ID = "superb/wav2vec2-base-superb-er"


class AudioEmotionModel:
    def __init__(self) -> None:
        # This checkpoint ships an audio feature extractor but no CTC tokenizer.
        # AutoProcessor attempts to load both, which prevents the model from starting.
        self.feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_ID)
        self.model = AutoModelForAudioClassification.from_pretrained(MODEL_ID)
        self.model.eval()

    def predict(self, waveform: np.ndarray) -> EmotionPrediction:
        inputs = self.feature_extractor(waveform, sampling_rate=16_000, return_tensors="pt")
        with torch.inference_mode():
            logits = self.model(**inputs).logits[0].cpu().numpy()
        return softmax_scores(np.asarray(logits), self.model.config.id2label)
