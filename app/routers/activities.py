from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import UserRole, User, ChurchActivity, SongUsage
from app.schemas.activities import (
    ChurchActivitySchema,
)
from app.schemas.songs import (
    SongCountByActivityResponse,
    SongCountByActivityFilters,
)
from app.dependencies import require_min_role


router = APIRouter()


@router.get(
    "/",
    status_code=200,
    response_model=list[ChurchActivitySchema],
    tags=["activities"],
    summary=(
        "(user:activity) Lists church activities"
    ),
)
def list_viewable_church_activities(
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
):
    # Todo: replace with user-permissions approach
    viewable_activity_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    query = (
        db.query(ChurchActivity)
        .filter(ChurchActivity.id.in_(viewable_activity_ids))
        .order_by(ChurchActivity.name.asc())
    )
    return query.all()


@router.get(
    "/songs/usages/summary",
    response_model=list[SongCountByActivityResponse],
    tags=["activities"],
    summary="(user:activity) Lists song usages by activity",
)
def song_usage_by_activity(
    filter_query: Annotated[SongCountByActivityFilters, Query()],
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
):
    usage_filters = []

    # Role-based activity restriction
    allowed_activity_ids = set(range(100))
    usage_filters.append(SongUsage.church_activity_id.in_(allowed_activity_ids))

    # Query param activity filter
    if filter_query.church_activity_id:
        effective_activities = set(allowed_activity_ids) & set(
            filter_query.church_activity_id
        )
        usage_filters.append(SongUsage.church_activity_id.in_(effective_activities))

    # Date filters
    from_date = filter_query.from_date or date(1900, 1, 1)
    to_date = filter_query.to_date or date(2100, 1, 1)
    usage_filters.append(SongUsage.used_date.between(from_date, to_date))

    results = (
        db.query(
            ChurchActivity.id.label("church_activity_id"),
            ChurchActivity.name.label("church_activity_name"),
            func.count(SongUsage.id).label("total_count"),
            func.count(func.distinct(SongUsage.song_id)).label("unique_count"),
        )
        .join(ChurchActivity, ChurchActivity.id == SongUsage.church_activity_id)
        .filter(*usage_filters)
        .group_by(
            ChurchActivity.id,
            ChurchActivity.name,
        )
        .order_by(ChurchActivity.name)
        .all()
    )

    return results
