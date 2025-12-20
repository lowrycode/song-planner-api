from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    Song,
    SongLyrics,
    SongUsage,
    SongUsageStats,
    UserRole,
    User,
    ChurchActivity,
)
from app.schemas.songs import (
    SongListFilters,
    SongBasicDetails,
    SongListUsageResponse,
    SongFullDetails,
    SongUsageSchema,
    SongUsageFilters,
    SongListUsageFilters,
    ActivityUsageStats,
    OverallActivityUsageStats,
    SongKeyFilters,
    SongKeyResponse,
)
from app.dependencies import require_min_role
from datetime import date


router = APIRouter()


@router.get("/", status_code=200, response_model=list[SongBasicDetails])
def list_songs(
    filter_query: Annotated[SongListFilters, Query()],
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
):

    query = db.query(Song)

    if filter_query.song_key is not None:
        query = query.filter(Song.song_key == filter_query.song_key)
    if filter_query.song_type:
        song_type = filter_query.song_type
        if song_type == "song":
            query = query.filter(Song.is_hymn == False)
        elif song_type == "hymn":
            query = query.filter(Song.is_hymn == True)
    if filter_query.lyric is not None:
        query = query.join(SongLyrics).filter(
            SongLyrics.song_id == Song.id,
            SongLyrics.content.ilike(f"%{filter_query.lyric}%"),
        )

    query = query.order_by(Song.first_line.asc())
    return query.all()


@router.get("/key-summary", status_code=200, response_model=list[SongKeyResponse])
def song_keys_overview(
    filter_query: Annotated[SongKeyFilters, Query()],
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
):

    # Default filters
    usage_filters = []

    # Role based filters
    # This approach breaks tests due to primary key auto-increment behaviour!
    # allowed_activity_ids = [0, 1, 2, 3]
    # Temp allow large range of numbers
    allowed_activity_ids = [n for n in range(100)]
    usage_filters.append(SongUsage.church_activity_id.in_(allowed_activity_ids))

    # Activity filters
    allowed_activites = allowed_activity_ids
    if filter_query.church_activity_id:
        effective_activites = list(
            set(allowed_activites) & set(filter_query.church_activity_id)
        )
    else:
        effective_activites = allowed_activites
    usage_filters.append(SongUsage.church_activity_id.in_(effective_activites))

    # Date filters
    from_date = filter_query.from_date or date(1900, 1, 1)
    to_date = filter_query.to_date or date(2100, 1, 1)
    usage_filters.append(SongUsage.used_date.between(from_date, to_date))

    # Unique filter
    count_expr = (
        func.count(func.distinct(SongUsage.song_id))
        if filter_query.unique
        else func.count(SongUsage.id)
    )

    query = (
        db.query(
            Song.song_key,
            count_expr.label("count"),
        )
        .join(SongUsage.song)
        .filter(*usage_filters)
        .group_by(Song.song_key)
        .order_by(count_expr.desc())
    )
    return query.all()


@router.get(
    "/usage-summary", status_code=200, response_model=list[SongListUsageResponse]
)
def list_songs_with_usage_summary(
    filter_query: Annotated[SongListUsageFilters, Query()],
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
):

    # Default filters
    song_filters = []
    usage_filters = []
    usage_stats_filters = []  # applied using ON (not WHERE) to show unused songs

    # Role based filters
    # This approach breaks tests due to primary key auto-increment behaviour!
    # allowed_activity_ids = [0, 1, 2, 3]
    # Temp allow large range of numbers
    allowed_activity_ids = [n for n in range(100)]
    usage_filters.append(SongUsage.church_activity_id.in_(allowed_activity_ids))
    usage_stats_filters.append(
        SongUsageStats.church_activity_id.in_(allowed_activity_ids)
    )

    # activity filters
    allowed_activites = allowed_activity_ids
    if filter_query.church_activity_id:
        effective_activites = list(
            set(allowed_activites) & set(filter_query.church_activity_id)
        )
    else:
        effective_activites = allowed_activites
    usage_filters.append(SongUsage.church_activity_id.in_(effective_activites))
    usage_stats_filters.append(
        SongUsageStats.church_activity_id.in_(effective_activites)
    )

    # Date filters
    from_date = filter_query.from_date or date(1900, 1, 1)
    to_date = filter_query.to_date or date(2100, 1, 1)
    usage_filters.append(SongUsage.used_date.between(from_date, to_date))

    # First or last filters
    first_last_filters = []
    if filter_query.first_used_in_range:
        first_last_filters.append(SongUsageStats.first_used.between(from_date, to_date))
    if filter_query.last_used_in_range:
        first_last_filters.append(SongUsageStats.last_used.between(from_date, to_date))

    if first_last_filters:
        # Get song_ids for filtering later
        subq_song_ids = (
            db.query(SongUsageStats.song_id)
            .filter(*usage_stats_filters, *first_last_filters)
            .distinct()
            .subquery()
        )
    else:
        subq_song_ids = None

    # Other filters
    if filter_query.song_key:
        song_filters.append(Song.song_key == filter_query.song_key)
    if filter_query.song_type:
        song_type = filter_query.song_type
        if song_type == "song":
            song_filters.append(Song.is_hymn == False)
        elif song_type == "hymn":
            song_filters.append(Song.is_hymn == True)
    if filter_query.lyric:
        lyrics_subquery = (
            db.query(SongLyrics.id)
            .filter(
                SongLyrics.song_id == Song.id,
                SongLyrics.content.ilike(f"%{filter_query.lyric}%"),
            )
            .exists()
        )
        song_filters.append(lyrics_subquery)

    # Usage sub-queries (both apply usage_filters)
    usage_counts_by_activity = (
        db.query(
            SongUsage.song_id.label("song_id"),
            SongUsage.church_activity_id.label("activity"),
            func.count(SongUsage.id).label("usage_count"),
        )
        .filter(*usage_filters)
        .group_by(SongUsage.song_id, SongUsage.church_activity_id)
    ).subquery()

    usage_counts_total = (
        db.query(
            SongUsage.song_id.label("song_id"),
            func.count(SongUsage.id).label("usage_count"),
        )
        .filter(*usage_filters)
        .group_by(SongUsage.song_id)
    ).subquery()

    usage_stats_join_condition = SongUsageStats.song_id == Song.id
    for f in usage_stats_filters:
        usage_stats_join_condition = usage_stats_join_condition & f

    # Overall query (applies usage_stats_filters)
    query = (
        db.query(
            Song.id.label("song_id"),
            Song.first_line,
            ChurchActivity.id.label("activity_id"),
            ChurchActivity.slug.label("activity_slug"),
            ChurchActivity.name.label("activity_name"),
            SongUsageStats.first_used,
            SongUsageStats.last_used,
            usage_counts_by_activity.c.usage_count.label("activity_usage_count"),
            usage_counts_total.c.usage_count.label("total_usage_count"),
        )
        .outerjoin(SongUsageStats, usage_stats_join_condition)
        .outerjoin(
            ChurchActivity,
            ChurchActivity.id == SongUsageStats.church_activity_id,
        )
        .outerjoin(
            usage_counts_by_activity,
            (usage_counts_by_activity.c.song_id == Song.id)
            & (usage_counts_by_activity.c.activity == ChurchActivity.id),
        )
        .outerjoin(usage_counts_total, usage_counts_total.c.song_id == Song.id)
    )

    # Apply other filters
    # query = query.filter(*usage_stats_filters)
    query = query.filter(*song_filters)

    # Filter further (using song_ids derived from first_last filters)
    if subq_song_ids is not None:
        query = query.filter(Song.id.in_(select(subq_song_ids)))

    # Query DB
    rows = query.all()

    # Format response
    result: dict[int, SongListUsageResponse] = {}

    for r in rows:
        if r.song_id not in result:
            result[r.song_id] = SongListUsageResponse(
                id=r.song_id,
                first_line=r.first_line,
                activities={},
                overall=OverallActivityUsageStats(
                    usage_count=r.total_usage_count or 0,
                    first_used=None,
                    last_used=None,
                ),
            )
        song = result[r.song_id]

        if r.activity_slug:
            song.activities[r.activity_slug] = ActivityUsageStats(
                id=r.activity_id,
                name=r.activity_name,
                usage_count=r.activity_usage_count or 0,
                first_used=r.first_used,
                last_used=r.last_used,
            )

            # Update overall first/last used
            if song.overall.first_used is None or (
                r.first_used and r.first_used < song.overall.first_used
            ):
                song.overall.first_used = r.first_used

            if song.overall.last_used is None or (
                r.last_used and r.last_used > song.overall.last_used
            ):
                song.overall.last_used = r.last_used

    # Fill missing activities with zero usage
    activity_map = {
        e.id: (e.slug, e.name)
        for e in db.query(ChurchActivity).filter(
            ChurchActivity.id.in_(effective_activites)
        )
    }

    for song in result.values():
        for activity_id, (slug, name) in activity_map.items():
            if slug not in song.activities:
                song.activities[slug] = ActivityUsageStats(
                    id=activity_id,
                    name=name,
                    usage_count=0,
                    first_used=None,
                    last_used=None,
                )

    return list(result.values())


@router.get("/{song_id}", status_code=200, response_model=SongFullDetails)
def song_full_details(
    song_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
):
    song = (
        db.query(Song)
        .options(
            joinedload(Song.lyrics),
            joinedload(Song.resources),
        )
        .filter(Song.id == song_id)
        .first()
    )

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    return song


@router.get("/{song_id}/usages", status_code=200, response_model=list[SongUsageSchema])
def song_usages(
    song_id: int,
    filters: Annotated[SongUsageFilters, Query()],
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
):
    # Ensure song exists
    if not db.query(Song.id).filter(Song.id == song_id).first():
        raise HTTPException(status_code=404, detail="Song not found")

    query = db.query(SongUsage).filter(SongUsage.song_id == song_id)

    # Apply filters
    if filters.used_after:
        query = query.filter(SongUsage.used_date >= filters.used_after)
    if filters.used_before:
        query = query.filter(SongUsage.used_date <= filters.used_before)
    if filters.church_activity_id:
        query = query.filter(
            SongUsage.church_activity_id.in_(filters.church_activity_id)
        )

    return query.all()
