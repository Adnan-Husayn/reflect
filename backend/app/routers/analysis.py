import logging

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas.emotion import ConflictRequest, FusionAnalysis
from app.utils.fusion import analyze

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["analysis"])


@router.post("/fusion", response_model=FusionAnalysis)
def analyze_fusion(payload: ConflictRequest) -> FusionAnalysis:
    """Fuse the latest reading from each channel and measure their disagreement.

    Stateless by design: the client holds the latest reading per channel and
    sends them together, so no session data is retained on the server. The
    per-channel scores are echoed back so the interface can always show the
    components beside the fused headline.
    """
    settings = get_settings()
    try:
        return analyze(payload.channels(), settings.conflict_threshold, settings.fusion_weights())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
