"""Session persistence.

Kept deliberately separate from the prediction routers. `/predict/*` and
`/analyze/fusion` remain pure: the evaluation harness drives them 1,440 times
per run, and if prediction persisted, every evaluation run would forge a
thousand sessions of fake user history.

There is no multipart endpoint here and no bytes-typed column in the schema, so
this API cannot store raw media regardless of what a caller sends.
"""

import logging
from collections import Counter

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session as OrmSession

from app.db.models import CheckIn, FusedReading, Reading, Session, SessionSummary, User, utcnow
from app.db.session import get_db
from app.routers.auth import resolve_user
from app.schemas.session import (
    BatchAccepted,
    CheckInIn,
    CheckInOut,
    DeletionReceipt,
    ReadingBatch,
    SessionDetail,
    SessionListItem,
    SessionOut,
    SummaryOut,
)
from app.security import SESSION_COOKIE
from app.utils.valence import mean_valence

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sessions"])


def current_user(
    reflect_session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: OrmSession = Depends(get_db),
) -> User:
    """Resolve the signed-in account, or refuse.

    Every session-scoped query already filtered on user_id, so this dependency
    is the whole of what auth changed on the read and write paths.
    """
    user = resolve_user(reflect_session, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return user


def _owned_session(session_id: str, db: OrmSession, user: User) -> Session:
    session = db.query(Session).filter(Session.id == session_id, Session.user_id == user.id).one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@router.post("/sessions", response_model=SessionOut, status_code=201)
def open_session(db: OrmSession = Depends(get_db), user: User = Depends(current_user)) -> Session:
    session = Session(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/sessions/{session_id}/readings", response_model=BatchAccepted)
def append_readings(
    session_id: str,
    batch: ReadingBatch,
    db: OrmSession = Depends(get_db),
    user: User = Depends(current_user),
) -> BatchAccepted:
    session = _owned_session(session_id, db, user)
    if not session.is_open:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This session has ended and cannot accept more readings.",
        )

    for reading in batch.readings:
        db.add(Reading(session_id=session.id, **reading.model_dump()))
    for fused in batch.fused:
        db.add(FusedReading(session_id=session.id, **fused.model_dump()))
    db.commit()

    return BatchAccepted(
        session_id=session.id,
        readings_added=len(batch.readings),
        fused_added=len(batch.fused),
    )


def _build_summary(session: Session, db: OrmSession) -> SessionSummary:
    readings = db.query(Reading).filter(Reading.session_id == session.id).all()
    fused = db.query(FusedReading).filter(FusedReading.session_id == session.id).all()

    # Valence and conflict rate read the FUSED readings only. Averaging
    # per-channel readings would let the facial channel dominate: it samples
    # every 2s against audio's 5s, so the mean would track the sampling rate
    # rather than the mood.
    valence = mean_valence([reading.scores for reading in fused])
    conflict_rate = sum(1 for reading in fused if reading.conflict) / len(fused) if fused else None
    labels = Counter(reading.label for reading in fused)
    channel_counts = Counter(reading.channel for reading in readings)

    return SessionSummary(
        session_id=session.id,
        n_readings=len(readings),
        n_fused_readings=len(fused),
        mean_valence=valence,
        conflict_rate=conflict_rate,
        dominant_label=labels.most_common(1)[0][0] if labels else None,
        channel_counts=dict(channel_counts),
        computed_at=utcnow(),
    )


@router.post("/sessions/{session_id}/end", response_model=SummaryOut)
def end_session(
    session_id: str,
    db: OrmSession = Depends(get_db),
    user: User = Depends(current_user),
) -> SessionSummary:
    session = _owned_session(session_id, db, user)
    if not session.is_open:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This session has already ended.")

    session.ended_at = utcnow()
    summary = _build_summary(session, db)
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


@router.get("/sessions", response_model=list[SessionListItem])
def list_sessions(db: OrmSession = Depends(get_db), user: User = Depends(current_user)) -> list[Session]:
    return db.query(Session).filter(Session.user_id == user.id).order_by(Session.started_at.desc()).all()


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: str, db: OrmSession = Depends(get_db), user: User = Depends(current_user)
) -> Session:
    return _owned_session(session_id, db, user)


def _delete_sessions(sessions: list[Session], db: OrmSession) -> DeletionReceipt:
    ids = [session.id for session in sessions]
    if not ids:
        return DeletionReceipt(
            deleted_sessions=0, deleted_readings=0, deleted_fused_readings=0, deleted_checkins=0
        )

    readings = db.query(Reading).filter(Reading.session_id.in_(ids)).count()
    fused = db.query(FusedReading).filter(FusedReading.session_id.in_(ids)).count()
    for session in sessions:
        db.delete(session)
    db.commit()
    return DeletionReceipt(
        deleted_sessions=len(ids),
        deleted_readings=readings,
        deleted_fused_readings=fused,
        deleted_checkins=0,
    )


@router.delete("/sessions/{session_id}", response_model=DeletionReceipt)
def delete_session(
    session_id: str, db: OrmSession = Depends(get_db), user: User = Depends(current_user)
) -> DeletionReceipt:
    """Erase one session and everything derived from it."""
    session = _owned_session(session_id, db, user)
    return _delete_sessions([session], db)


@router.delete("/users/me/data", response_model=DeletionReceipt)
def delete_all_user_data(
    db: OrmSession = Depends(get_db), user: User = Depends(current_user)
) -> DeletionReceipt:
    """Withdraw entirely: every session, reading and check-in for this user.

    Participants must be able to withdraw their data, and a delete that only
    marks rows inactive would not be a withdrawal. These rows are really gone.
    """
    sessions = db.query(Session).filter(Session.user_id == user.id).all()
    receipt = _delete_sessions(sessions, db)

    checkins = db.query(CheckIn).filter(CheckIn.user_id == user.id)
    deleted_checkins = checkins.count()
    checkins.delete(synchronize_session=False)
    db.commit()

    return receipt.model_copy(update={"deleted_checkins": deleted_checkins})


@router.post("/checkins", response_model=CheckInOut, status_code=201)
def record_checkin(
    payload: CheckInIn, db: OrmSession = Depends(get_db), user: User = Depends(current_user)
) -> CheckIn:
    """Record one self-report score.

    Minimal on purpose — the PHQ-8 form itself is a later milestone. It exists
    now because check-ins need calendar time to accumulate, and a table with no
    write path would collect nothing.
    """
    existing = (
        db.query(CheckIn)
        .filter(
            CheckIn.user_id == user.id,
            CheckIn.taken_on == payload.taken_on,
            CheckIn.instrument == payload.instrument,
        )
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A {payload.instrument} check-in already exists for {payload.taken_on}.",
        )

    checkin = CheckIn(user_id=user.id, **payload.model_dump())
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


@router.get("/checkins", response_model=list[CheckInOut])
def list_checkins(db: OrmSession = Depends(get_db), user: User = Depends(current_user)) -> list[CheckIn]:
    return db.query(CheckIn).filter(CheckIn.user_id == user.id).order_by(CheckIn.taken_on.desc()).all()
