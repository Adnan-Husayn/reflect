import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.schemas.emotion import EmotionPrediction
from app.utils.emotions import softmax_scores

MODEL_ID = "j-hartmann/emotion-english-distilroberta-base"


class TextEmotionModel:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
        self.model.eval()

    def predict(self, text: str) -> EmotionPrediction:
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.inference_mode():
            logits = self.model(**inputs).logits[0].cpu().numpy()
        return softmax_scores(np.asarray(logits), self.model.config.id2label)
