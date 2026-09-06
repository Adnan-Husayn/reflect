"""Instrument definitions, served so the form renders from the server's copy.

Keeping the item text in one place means the questionnaire the participant
answers and the definition the score is computed from cannot drift apart.
"""

from fastapi import APIRouter, HTTPException

from app.instruments import INSTRUMENTS
from app.schemas.instrument import InstrumentOut

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/{code}", response_model=InstrumentOut)
def get_instrument(code: str) -> InstrumentOut:
    instrument = INSTRUMENTS.get(code)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Unknown instrument: {code}.")
    return InstrumentOut(
        code=instrument.code,
        name=instrument.name,
        prompt=instrument.prompt,
        max_score=instrument.max_score,
        items=[{"id": item.id, "text": item.text} for item in instrument.items],
        options=[{"value": option.value, "label": option.label} for option in instrument.options],
    )
