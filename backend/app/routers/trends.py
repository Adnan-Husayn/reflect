"""Longitudinal trends over recorded sessions.

Aggregation happens here rather than in the browser. The valence definition
already lives in `app/utils/valence.py`; a second implementation in TypeScript
would drift from it, and the definition of the tracked construct needs to stay
in one file for M5 to be able to defend it.

Reads `session_summaries` rather than scanning `readings`, which is what the
rollup exists for.
"""

from datetime import UTC, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as OrmSession

from app.db.models import CheckIn, Session, SessionSummary, User
from app.db.session import get_db
from app.routers.sessions import current_user
from app.schemas.trends import CorrelationOut, TrendBucket, TrendsOut
from app.utils.correlation import correlate
from app.utils.trends import (
    MINIMUM_READINGS_PER_DAY,
    ROLLING_WINDOW_DAYS,
    SessionRollup,
    build_trends,
)

router = APIRouter(tags=["trends"])

DEFAULT_DAYS = 30
MAX_DAYS = 365


@router.get("/trends", response_model=TrendsOut)
def get_trends(
    days: int = Query(DEFAULT_DAYS, ge=1, le=MAX_DAYS),
    db: OrmSession = Depends(get_db),
    user: User = Depends(current_user),
) -> TrendsOut:
    # UTC, matching how the timestamps are stored and bucketed. date.today()
    # is the server's local date, so wherever local and UTC dates differ the
    # range and the buckets disagree and a session recorded moments ago falls
    # outside the window it belongs to.
    end = datetime.now(UTC).date()
    start = end - timedelta(days=days - 1)

    # Joining on the summary excludes sessions that are still open: an
    # in-progress session has no rollup and must not be drawn as if it did.
    # Bounded by the requested range rather than loading every session ever
    # recorded and discarding the ones outside it.
    range_start = datetime.combine(start, time.min, tzinfo=UTC)
    rows = (
        db.query(Session.started_at, SessionSummary)
        .join(SessionSummary, SessionSummary.session_id == Session.id)
        .filter(
            Session.user_id == user.id,
            Session.ended_at.isnot(None),
            Session.started_at >= range_start,
        )
        .all()
    )

    rollups = [
        SessionRollup(
            day=started_at.date(),
            n_fused_readings=summary.n_fused_readings,
            mean_valence=summary.mean_valence,
            conflict_rate=summary.conflict_rate,
            channel_counts=dict(summary.channel_counts or {}),
        )
        for started_at, summary in rows
    ]

    buckets = build_trends(rollups, start, end)

    checkins = (
        db.query(CheckIn.taken_on, CheckIn.score)
        .filter(
            CheckIn.user_id == user.id,
            CheckIn.instrument == "PHQ-8",
            CheckIn.taken_on >= start,
        )
        .all()
    )
    scores_by_day = dict(checkins)

    # Only days the buckets actually withheld are excluded from pairing: a
    # check-in on a day with no usable session contributes no pair.
    correlation = correlate({bucket.day: bucket.mean_valence for bucket in buckets}, scores_by_day)
    return TrendsOut(
        start=start,
        end=end,
        buckets=[
            TrendBucket(
                date=bucket.day,
                n_sessions=bucket.n_sessions,
                n_fused_readings=bucket.n_fused_readings,
                mean_valence=bucket.mean_valence,
                rolling_valence=bucket.rolling_valence,
                conflict_rate=bucket.conflict_rate,
                channel_counts=bucket.channel_counts,
                sufficient=bucket.sufficient,
                checkin_score=scores_by_day.get(bucket.day),
            )
            for bucket in buckets
        ],
        minimum_readings_per_day=MINIMUM_READINGS_PER_DAY,
        rolling_window_days=ROLLING_WINDOW_DAYS,
        correlation=CorrelationOut(r=correlation.r, n=correlation.n, minimum_pairs=correlation.minimum_pairs),
    )
