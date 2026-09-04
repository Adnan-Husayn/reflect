import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.config import get_settings
from app.schemas.emotion import EmotionPrediction, LiveAudioAnalysis, TextPredictionRequest
from app.utils.audio import decode_audio
from app.utils.image import decode_and_crop_largest_face

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predict", tags=["predictions"])

AUDIO_TYPES = {"audio/webm", "audio/wav", "audio/wave", "audio/x-wav"}
IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


def get_model(request: Request, name: str):
    model = request.app.state.models.get(name)
    if model is None:
        labels = {"text": "Text", "audio": "Audio", "facial": "Facial", "speech": "Speech transcription"}
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{labels[name]} emotion model is currently unavailable.",
        )
    return model


async def read_limited_upload(upload: UploadFile, maximum_size: int) -> bytes:
    content = await upload.read(maximum_size + 1)
    await upload.close()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > maximum_size:
        raise HTTPException(status_code=413, detail="The uploaded file exceeds the size limit.")
    return content


@router.post("/text", response_model=EmotionPrediction)
def predict_text(payload: TextPredictionRequest, request: Request) -> EmotionPrediction:
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text input cannot be empty.")
    if len(payload.text) > get_settings().max_text_characters:
        raise HTTPException(status_code=400, detail="Text input exceeds the character limit.")
    return get_model(request, "text").predict(payload.text.strip())


@router.post("/audio", response_model=EmotionPrediction)
async def predict_audio(request: Request, file: UploadFile = File(...)) -> EmotionPrediction:
    if file.content_type not in AUDIO_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported audio format.")
    audio_bytes = await read_limited_upload(file, get_settings().max_audio_bytes)
    try:
        waveform = decode_audio(audio_bytes)
    except Exception:
        logger.warning("audio preprocessing failed")
        raise HTTPException(status_code=400, detail="The uploaded audio could not be processed.") from None
    return get_model(request, "audio").predict(waveform)


@router.post("/live/audio", response_model=LiveAudioAnalysis)
async def analyze_live_audio(request: Request, file: UploadFile = File(...)) -> LiveAudioAnalysis:
    """Analyze one complete microphone segment without storing its audio or text."""
    if file.content_type not in AUDIO_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported audio format.")
    audio_bytes = await read_limited_upload(file, get_settings().max_audio_bytes)
    try:
        waveform = decode_audio(audio_bytes)
    except Exception:
        logger.warning("live audio preprocessing failed")
        raise HTTPException(status_code=400, detail="The uploaded audio could not be processed.") from None

    audio_prediction = get_model(request, "audio").predict(waveform)
    transcript = get_model(request, "speech").transcribe(waveform)
    text_prediction = get_model(request, "text").predict(transcript) if transcript else None
    return LiveAudioAnalysis(
        transcript=transcript,
        audio_prediction=audio_prediction,
        text_prediction=text_prediction,
    )


@router.post("/facial", response_model=EmotionPrediction)
async def predict_facial(request: Request, file: UploadFile = File(...)) -> EmotionPrediction:
    if file.content_type not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image format.")
    image_bytes = await read_limited_upload(file, get_settings().max_image_bytes)
    try:
        face_image = decode_and_crop_largest_face(image_bytes)
    except LookupError:
        raise HTTPException(status_code=400, detail="No face was detected in the captured image.") from None
    except ValueError:
        raise HTTPException(status_code=400, detail="The uploaded image could not be processed.") from None
    return get_model(request, "facial").predict(face_image)
