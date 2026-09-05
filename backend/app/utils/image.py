from io import BytesIO

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError


def decode_and_crop_largest_face(image_bytes: bytes) -> Image.Image:
    """Return the largest detected face so v0.1 stays single-person and deterministic."""
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError("The uploaded image could not be processed.") from error

    image_array = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
    if len(faces) == 0:
        raise LookupError("No face was detected in the captured image.")

    x, y, width, height = max(faces, key=lambda face: int(face[2]) * int(face[3]))
    # A small margin keeps expressions near the edge of a detected face available.
    margin = int(max(width, height) * 0.12)
    left, top = max(0, x - margin), max(0, y - margin)
    right = min(image.width, x + width + margin)
    bottom = min(image.height, y + height + margin)
    return image.crop((left, top, right, bottom))
