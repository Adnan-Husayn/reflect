import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

from app.schemas.emotion import EmotionPrediction
from app.utils.emotions import softmax_scores

# A separate candidate from the original checkpoint. The UI describes this as a
# visible-expression indicator rather than a measurement of internal emotion.
MODEL_ID = "dima806/facial_emotions_image_detection"


class FacialEmotionModel:
    def __init__(self) -> None:
        self.processor = AutoImageProcessor.from_pretrained(MODEL_ID)
        self.model = AutoModelForImageClassification.from_pretrained(MODEL_ID)
        self.model.eval()

    def predict(self, face_image: Image.Image) -> EmotionPrediction:
        inputs = self.processor(images=face_image, return_tensors="pt")
        with torch.inference_mode():
            logits = self.model(**inputs).logits[0].cpu().numpy()
        return softmax_scores(np.asarray(logits), self.model.config.id2label)
