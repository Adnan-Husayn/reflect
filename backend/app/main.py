import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.audio_emotion import AudioEmotionModel
from app.models.facial_emotion import FacialEmotionModel
from app.models.speech_transcription import SpeechTranscriptionModel
from app.models.text_emotion import TextEmotionModel
from app.routers.analysis import router as analysis_router
from app.routers.auth import router as auth_router
from app.routers.export import router as export_router
from app.routers.instruments import router as instruments_router
from app.routers.predictions import router as prediction_router
from app.routers.sessions import router as sessions_router
from app.routers.trends import router as trends_router
from app.routers.wellbeing import router as wellbeing_router
from app.schemas.emotion import HealthResponse

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_models() -> dict[str, object | None]:
    """Isolate failures so a missing model does not disable the other modalities."""
    model_factories = {
        "text": TextEmotionModel,
        "audio": AudioEmotionModel,
        "facial": FacialEmotionModel,
        "speech": SpeechTranscriptionModel,
    }
    models: dict[str, object | None] = {}
    for name, factory in model_factories.items():
        try:
            models[name] = factory()
            logger.info("%s emotion model loaded", name)
        except Exception:
            models[name] = None
            logger.exception("%s emotion model could not be loaded", name)
    return models


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.models = load_models()
    yield


settings = get_settings()
app = FastAPI(
    title="Reflect — PCS26/146 Emotion Analysis API",
    version="0.3.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    # Required for the session cookie to travel. A wildcard origin is
    # invalid with credentials, so frontend_origin must stay exact.
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(prediction_router)
app.include_router(analysis_router)
app.include_router(sessions_router)
app.include_router(trends_router)
app.include_router(instruments_router)
app.include_router(auth_router)
app.include_router(wellbeing_router)
app.include_router(export_router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    models = {name: model is not None for name, model in app.state.models.items()}
    return HealthResponse(status="ok" if all(models.values()) else "degraded", models=models)
