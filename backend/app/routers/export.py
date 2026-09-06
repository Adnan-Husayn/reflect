"""CSV export of an account's own derived data.

Exists so the report can be written from the numbers rather than from
screenshots, and so a participant can take their data with them.

Only derived values leave here — the same rule the schema enforces. There is
no audio, no frame and no transcript to export, because none is stored.
"""

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as OrmSession

from app.db.models import CheckIn, Session, SessionSummary, User
from app.db.session import get_db
from app.routers.sessions import current_user

router = APIRouter(prefix="/export", tags=["export"])

SESSION_COLUMNS = [
    "session_id",
    "started_at",
    "ended_at",
    "n_readings",
    "n_fused_readings",
    "mean_valence",
    "conflict_rate",
    "dominant_label",
    "text_readings",
    "voice_readings",
    "face_readings",
]

CHECKIN_COLUMNS = ["taken_on", "instrument", "score", "responses"]


def _csv_response(columns: list[str], rows: list[list], filename: str) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sessions.csv")
def export_sessions(
    db: OrmSession = Depends(get_db), user: User = Depends(current_user)
) -> StreamingResponse:
    """One row per completed session, from the rollups."""
    rows = (
        db.query(Session, SessionSummary)
        .join(SessionSummary, SessionSummary.session_id == Session.id)
        .filter(Session.user_id == user.id)
        .order_by(Session.started_at)
        .all()
    )
    return _csv_response(
        SESSION_COLUMNS,
        [
            [
                session.id,
                session.started_at.isoformat(),
                session.ended_at.isoformat() if session.ended_at else "",
                summary.n_readings,
                summary.n_fused_readings,
                "" if summary.mean_valence is None else round(summary.mean_valence, 4),
                "" if summary.conflict_rate is None else round(summary.conflict_rate, 4),
                summary.dominant_label or "",
                (summary.channel_counts or {}).get("text", 0),
                (summary.channel_counts or {}).get("voice", 0),
                (summary.channel_counts or {}).get("face", 0),
            ]
            for session, summary in rows
        ],
        "reflect-sessions.csv",
    )


@router.get("/checkins.csv")
def export_checkins(
    db: OrmSession = Depends(get_db), user: User = Depends(current_user)
) -> StreamingResponse:
    """One row per check-in, with the item responses kept alongside the total.

    Item-level answers are what allow rescoring, and they are what a methods
    section describes.
    """
    checkins = (
        db.query(CheckIn)
        .filter(CheckIn.user_id == user.id)
        .order_by(CheckIn.taken_on, CheckIn.instrument)
        .all()
    )
    return _csv_response(
        CHECKIN_COLUMNS,
        [
            [
                checkin.taken_on.isoformat(),
                checkin.instrument,
                checkin.score,
                ";".join(f"{item}={value}" for item, value in sorted(checkin.responses.items())),
            ]
            for checkin in checkins
        ],
        "reflect-checkins.csv",
    )
