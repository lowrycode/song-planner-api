from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    SongUsage,
    SongYouTubeLink,
)
from app.schemas.songs import (
    SongYouTubeLinkWithUsageResponse,
    UsageContextFilters,
)
from app.dependencies import require_cron_api_key, get_cron_allowed_church_activity_ids
from app.utils.songs import (
    get_effective_activity_ids,
)


router = APIRouter()


@router.get(
    "/songs/{song_id}/youtube-links/best",
    response_model=SongYouTubeLinkWithUsageResponse,
    tags=["cron"],
    summary="(cron) Retrieves the most recent featured YouTube link",
)
def get_best_song_youtube_link_cron(
    song_id: int,
    filters: Annotated[UsageContextFilters, Query()],
    db: Session = Depends(get_db),
    _: None = Depends(require_cron_api_key),
    allowed_activity_ids: set[int] = Depends(get_cron_allowed_church_activity_ids),
):
    effective_activity_ids = get_effective_activity_ids(
        allowed_activity_ids=allowed_activity_ids,
        filter_activity_ids=filters.church_activity_id,
    )

    if not effective_activity_ids:
        raise HTTPException(status_code=404, detail="YouTube link not found")

    base_query = (
        db.query(SongYouTubeLink)
        .join(SongYouTubeLink.song_usage)
        .filter(
            SongUsage.song_id == song_id,
            SongUsage.church_activity_id.in_(effective_activity_ids),
        )
    )

    if filters.from_date is not None:
        base_query = base_query.filter(SongUsage.used_date >= filters.from_date)

    if filters.to_date is not None:
        base_query = base_query.filter(SongUsage.used_date <= filters.to_date)

    link = base_query.order_by(
        SongYouTubeLink.is_featured.desc(),
        SongUsage.used_date.desc(),
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="YouTube link not found")

    return SongYouTubeLinkWithUsageResponse(
        id=link.id,
        url=link.url,
        start_seconds=link.start_seconds,
        end_seconds=link.end_seconds,
        is_featured=link.is_featured,
        title=link.title,
        description=link.description,
        thumbnail_key=link.thumbnail_key,
        usage_id=link.song_usage_id,
        used_date=link.song_usage.used_date,
        church_activity_id=link.song_usage.church_activity_id,
    )
