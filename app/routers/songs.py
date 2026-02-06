from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, cast, Numeric, and_
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import (
    Song,
    SongLyrics,
    SongUsage,
    SongUsageStats,
    SongThemes,
    SongThemeEmbeddings,
    SongLyricEmbeddings,
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
    SongTypeFilters,
    SongTypeResponse,
    SongThemeSearchRequest,
    SongThemeSearchResponse,
)
from app.dependencies import require_min_role, get_allowed_church_activity_ids
from app.utils.rag import get_embeddings, EmbeddingServiceUnavailable
from app.utils.songs import (
    get_effective_activity_ids,
    build_song_usage_filters,
    build_song_usage_stats_filters,
    build_song_filters,
    resolve_usage_filtered_song_ids,
)


router = APIRouter()


@router.get(
    "",
    status_code=200,
    response_model=list[SongBasicDetails],
    tags=["songs"],
    summary="(public) Lists all songs",
)
def list_songs(
    filter_query: Annotated[SongListFilters, Query()],
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
):

    song_filters = build_song_filters(
        db=db,
        song_key=filter_query.song_key,
        song_type=filter_query.song_type,
        lyric=filter_query.lyric,
    )

    query = db.query(Song).filter(*song_filters).order_by(Song.first_line.asc())
    return query.all()


@router.get(
    "/usages/keys",
    status_code=200,
    response_model=dict[str, int],
    tags=["songs"],
    summary="(user:activity) Summarises keys for used songs",
)
def song_keys_overview(
    filter_query: Annotated[SongKeyFilters, Query()],
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
    allowed_activity_ids: set[int] = Depends(get_allowed_church_activity_ids),
):

    # Activity filters
    effective_activity_ids = get_effective_activity_ids(
        allowed_activity_ids=allowed_activity_ids,
        filter_activity_ids=filter_query.church_activity_id,
    )

    # Usage Filters
    usage_filters = build_song_usage_filters(
        effective_activity_ids=effective_activity_ids,
        from_date=filter_query.from_date,
        to_date=filter_query.to_date,
    )

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

    results = query.all()
    response = {song_key: count for song_key, count in results}
    return response


@router.get(
    "/usages/types",
    status_code=200,
    response_model=SongTypeResponse,
    tags=["songs"],
    summary="(user:activity) Summarises song types for used songs",
)
def song_type_overview(
    filter_query: Annotated[SongTypeFilters, Query()],
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
    allowed_activity_ids: set[int] = Depends(get_allowed_church_activity_ids),
):

    # Activity filters
    effective_activity_ids = get_effective_activity_ids(
        allowed_activity_ids=allowed_activity_ids,
        filter_activity_ids=filter_query.church_activity_id,
    )

    # Usage Filters
    usage_filters = build_song_usage_filters(
        effective_activity_ids=effective_activity_ids,
        from_date=filter_query.from_date,
        to_date=filter_query.to_date,
    )

    # Unique filter
    count_expr = (
        func.count(func.distinct(SongUsage.song_id))
        if filter_query.unique
        else func.count(SongUsage.id)
    )

    results = (
        db.query(
            Song.is_hymn,
            count_expr.label("count"),
        )
        .join(SongUsage.song)
        .filter(*usage_filters)
        .group_by(Song.is_hymn)
        .order_by(count_expr.desc())
    )

    counts = {"hymn": 0, "song": 0}
    for is_hymn, count in results:
        key = "hymn" if is_hymn else "song"
        counts[key] = count

    return counts


@router.get(
    "/usages/summary",
    status_code=200,
    response_model=list[SongListUsageResponse],
    tags=["songs"],
    summary="(user:activity) Summarises keys for used songs",
)
def list_songs_with_usage_summary(
    filter_query: Annotated[SongListUsageFilters, Query()],
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
    allowed_activity_ids: set[int] = Depends(get_allowed_church_activity_ids),
):

    # Activities Filter
    effective_activity_ids = get_effective_activity_ids(
        allowed_activity_ids=allowed_activity_ids,
        filter_activity_ids=filter_query.church_activity_id,
    )
    if not effective_activity_ids:
        return []

    # Song filters
    song_filters = build_song_filters(
        db=db,
        song_key=filter_query.song_key,
        song_type=filter_query.song_type,
        lyric=filter_query.lyric,
    )

    # Usage Filters
    usage_filters = build_song_usage_filters(
        effective_activity_ids=effective_activity_ids,
        from_date=filter_query.from_date,
        to_date=filter_query.to_date,
    )

    # Usage Stats Filters
    usage_stats_filters = build_song_usage_stats_filters(
        effective_activity_ids=effective_activity_ids,
        from_date=filter_query.from_date,
        to_date=filter_query.to_date,
        first_used_in_range=filter_query.first_used_in_range,
        last_used_in_range=filter_query.last_used_in_range,
    )

    # Song IDs subquery filtered by usages
    eligible_song_ids_from_usage = resolve_usage_filtered_song_ids(
        db=db,
        first_used_in_range=filter_query.first_used_in_range,
        last_used_in_range=filter_query.last_used_in_range,
        used_in_range=filter_query.used_in_range,
        usage_filters=usage_filters,
        usage_stats_filters=usage_stats_filters,
    )

    # Usage Aggregate sub-queries
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

    usage_stats_join_condition = and_(
        SongUsageStats.song_id == Song.id,
        *usage_stats_filters,
    )

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
    query = query.filter(*song_filters)

    # Filter further (using song_ids after all usage filters are resolved)
    if eligible_song_ids_from_usage is not None:
        query = query.filter(Song.id.in_(select(eligible_song_ids_from_usage)))

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
            ChurchActivity.id.in_(effective_activity_ids)
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


@router.get(
    "/{song_id}",
    status_code=200,
    response_model=SongFullDetails,
    tags=["songs"],
    summary="(public) Retrieve song details without usage data",
)
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


@router.get(
    "/{song_id}/usages",
    status_code=200,
    response_model=list[SongUsageSchema],
    tags=["songs"],
    summary="(user:activity) List song usages for specified song",
)
def song_usages(
    song_id: int,
    filters: Annotated[SongUsageFilters, Query()],
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
    allowed_activity_ids: set[int] = Depends(get_allowed_church_activity_ids),
):

    # Ensure song exists
    if not db.query(Song.id).filter_by(id=song_id).first():
        raise HTTPException(status_code=404, detail="Song not found")

    effective_activity_ids = get_effective_activity_ids(
        allowed_activity_ids=allowed_activity_ids,
        filter_activity_ids=filters.church_activity_id,
    )

    if not effective_activity_ids:
        return []

    usage_filters = build_song_usage_filters(
        effective_activity_ids=effective_activity_ids,
        from_date=filters.from_date,
        to_date=filters.to_date,
    )

    query = (
        db.query(SongUsage)
        .filter(SongUsage.song_id == song_id)
        .filter(*usage_filters)
    )

    return query.all()


@router.post(
    "/by-theme",
    response_model=list[SongThemeSearchResponse],
    tags=["songs"],
    summary="(user) Retrieve top_k songs by similarity to given themes",
)
def get_songs_by_theme(
    req: SongThemeSearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role(UserRole.normal)),
):
    try:
        input_embedding = get_embeddings([req.themes])[0]
    except EmbeddingServiceUnavailable:
        raise HTTPException(status_code=503)

    if req.search_type == "lyric":
        embedding_model = SongLyricEmbeddings
        base_query = (
            select(
                Song.id,
                Song.first_line,
                SongThemes.content.label("themes"),
            )
            .select_from(embedding_model)
            .join(SongLyrics, SongLyrics.id == embedding_model.song_lyrics_id)
            .join(Song, Song.id == SongLyrics.song_id)
            .outerjoin(SongThemes, SongThemes.song_lyrics_id == SongLyrics.id)
        )
    else:
        embedding_model = SongThemeEmbeddings
        base_query = (
            select(
                Song.id,
                Song.first_line,
                SongThemes.content.label("themes"),
            )
            .select_from(embedding_model)
            .join(SongThemes, SongThemes.id == embedding_model.song_themes_id)
            .join(SongLyrics, SongLyrics.id == SongThemes.song_lyrics_id)
            .join(Song, Song.id == SongLyrics.song_id)
        )

    distance = embedding_model.embedding.cosine_distance(input_embedding)
    similarity = func.greatest(0, func.least(1, 1 - distance))
    match_expr = cast(similarity * 100, Numeric(4, 1))
    match_score = match_expr.label("match_score")

    stmt = base_query.add_columns(match_score)

    if req.min_match_score is not None:
        stmt = stmt.where(match_expr >= req.min_match_score)

    stmt = stmt.order_by(match_score.desc()).limit(req.top_k)

    results = db.execute(stmt).all()
    return results
