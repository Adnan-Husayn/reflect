"""The wellbeing surface.

Reports observations over a trailing window. It never reports a state, and it
never grades anything: the interface says "more low-valence readings than
usual", and never "you are distressed".
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as OrmSession

from app.config import get_settings
from app.content.self_care import prompts_for
from app.db.models import FusedReading, Session, User
from app.db.session import get_db
from app.routers.sessions import current_user
from app.schemas.wellbeing import DayOut, PromptOut, WellbeingOut
from app.utils.distress import assess, summarise_days, to_reading_valences
from app.utils.trends import day_range

router = APIRouter(tags=["wellbeing"])


@router.get("/wellbeing", response_model=WellbeingOut)
def get_wellbeing(db: OrmSession = Depends(get_db), user: User = Depends(current_user)) -> WellbeingOut:
    settings = get_settings()
    # UTC, matching how timestamps are stored and how trends buckets them.
    end = datetime.now(UTC).date()
    start = end - timedelta(days=settings.distress_window_days - 1)
    window = day_range(start, end)

    # Per-reading rather than the rollup: the construct is a share of readings
    # below a threshold, which a daily mean cannot recover.
    rows = (
        db.query(FusedReading.t, FusedReading.scores, FusedReading.conflict)
        .join(Session, Session.id == FusedReading.session_id)
        .filter(Session.user_id == user.id, Session.ended_at.isnot(None))
        .all()
    )
    readings = to_reading_valences([(t.date(), scores, conflict) for t, scores, conflict in rows])

    observations = summarise_days(
        readings,
        window,
        minimum_readings=settings.distress_minimum_readings_per_day,
        low_valence_threshold=settings.distress_low_valence,
    )
    assessment = assess(
        observations,
        low_valence_share=settings.distress_low_valence_share,
        conflict_share=settings.distress_conflict_share,
        sustained_days=settings.distress_sustained_days,
        minimum_days=settings.distress_minimum_days,
    )

    prompts = prompts_for(
        status=assessment.status,
        sustained_low_valence=assessment.sustained_low_valence,
        sustained_conflict=assessment.sustained_conflict,
    )

    return WellbeingOut(
        status=assessment.status,
        days_with_data=assessment.days_with_data,
        low_valence_days=assessment.low_valence_days,
        conflict_days=assessment.conflict_days,
        sustained_low_valence=assessment.sustained_low_valence,
        sustained_conflict=assessment.sustained_conflict,
        window_days=assessment.window_days,
        sustained_days_required=assessment.sustained_days_required,
        minimum_days=assessment.minimum_days,
        days=[
            DayOut(
                date=day.day,
                n_readings=day.n_readings,
                low_valence_share=day.low_valence_share,
                conflict_share=day.conflict_share,
                sufficient=day.sufficient,
            )
            for day in assessment.days
        ],
        prompts=[PromptOut(key=p.key, observation=p.observation, suggestion=p.suggestion) for p in prompts],
        low_valence_threshold=settings.distress_low_valence,
        low_valence_share_threshold=settings.distress_low_valence_share,
        conflict_share_threshold=settings.distress_conflict_share,
    )
