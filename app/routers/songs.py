from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, cast, Numeric
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import (
    Song,
    SongLyrics,
    SongUsage,
    SongUsageStats,
    SongThemes,
    SongThemeEmbeddings,
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

    query = db.query(Song)

    if filter_query.song_key is not None:
        query = query.filter(Song.song_key == filter_query.song_key)
    if filter_query.song_type:
        song_type = filter_query.song_type
        if song_type == "song":
            query = query.filter(Song.is_hymn.is_(False))
        elif song_type == "hymn":
            query = query.filter(Song.is_hymn.is_(True))
    if filter_query.lyric is not None:
        query = query.join(SongLyrics).filter(
            SongLyrics.song_id == Song.id,
            SongLyrics.content.ilike(f"%{filter_query.lyric}%"),
        )

    query = query.order_by(Song.first_line.asc())
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

    # Default filters
    usage_filters = []

    # User access based filters
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

    # Default filters
    usage_filters = []

    # User access based filters
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

    # Default filters
    song_filters = []
    usage_filters = []
    usage_stats_filters = []  # applied using ON (not WHERE) to show unused songs

    # Combine allowed activities with filtered activities in url params
    if filter_query.church_activity_id:
        effective_activities = allowed_activity_ids & set(
            filter_query.church_activity_id
        )
    else:
        effective_activities = allowed_activity_ids

    effective_activities = list(effective_activities)
    if not effective_activities:
        return []

    # Activities filter
    usage_filters.append(SongUsage.church_activity_id.in_(effective_activities))
    usage_stats_filters.append(
        SongUsageStats.church_activity_id.in_(effective_activities)
    )

    # Date filters
    from_date = filter_query.from_date or date(1900, 1, 1)
    to_date = filter_query.to_date or date(2100, 1, 1)
    usage_filters.append(SongUsage.used_date.between(from_date, to_date))

    # Build song_id filter once, using set logic instead of nested queries
    song_id_filters = None

    # First/last and used_in_range filters
    if (
        filter_query.first_used_in_range
        or filter_query.last_used_in_range
        or filter_query.used_in_range
    ):
        filters_to_apply = []

        if filter_query.first_used_in_range or filter_query.last_used_in_range:
            first_last_filters = []
            if filter_query.first_used_in_range:
                first_last_filters.append(
                    SongUsageStats.first_used.between(from_date, to_date)
                )
            if filter_query.last_used_in_range:
                first_last_filters.append(
                    SongUsageStats.last_used.between(from_date, to_date)
                )

            song_ids_first_last = (
                db.query(SongUsageStats.song_id)
                .filter(*usage_stats_filters, *first_last_filters)
                .distinct()
            )
            filters_to_apply.append(song_ids_first_last)

        if filter_query.used_in_range:
            song_ids_used = (
                db.query(SongUsage.song_id).filter(*usage_filters).distinct()
            )
            filters_to_apply.append(song_ids_used)

        # Combine using intersection if both filters present
        if len(filters_to_apply) == 2:
            song_id_filters = (
                filters_to_apply[0].intersect(filters_to_apply[1]).subquery()
            )
        else:
            song_id_filters = filters_to_apply[0].subquery()

    # Other filters
    if filter_query.song_key:
        song_filters.append(Song.song_key == filter_query.song_key)
    if filter_query.song_type:
        song_type = filter_query.song_type
        if song_type == "song":
            song_filters.append(Song.is_hymn.is_(False))
        elif song_type == "hymn":
            song_filters.append(Song.is_hymn.is_(True))
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
    if song_id_filters is not None:
        query = query.filter(Song.id.in_(select(song_id_filters)))

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
            ChurchActivity.id.in_(effective_activities)
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
    if not db.query(Song).filter_by(id=song_id).first():
        raise HTTPException(status_code=404, detail="Song not found")

    # Return early if no allowed_activity_ids
    if not allowed_activity_ids:
        return []

    query = (
        db.query(SongUsage)
        .filter(SongUsage.song_id == song_id)
        .filter(SongUsage.church_activity_id.in_(allowed_activity_ids))
    )

    if filters.from_date:
        query = query.filter(SongUsage.used_date >= filters.from_date)
    if filters.to_date:
        query = query.filter(SongUsage.used_date <= filters.to_date)
    if filters.church_activity_id:
        effective_ids = set(filters.church_activity_id) & allowed_activity_ids
        query = query.filter(SongUsage.church_activity_id.in_(effective_ids))

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
    # Get embedding
    try:
        input_embedding = get_embeddings([req.themes])[0]

        # Mock embedding for testing!!
        # from tmp.defender import defender_embedding
        # input_embedding = defender_embedding
    except EmbeddingServiceUnavailable:
        raise HTTPException(status_code=503)

    # Define distance logic
    distance = SongThemeEmbeddings.embedding.cosine_distance(input_embedding)
    similarity = func.greatest(0, func.least(1, 1 - distance))
    match_expr = cast(similarity * 100, Numeric(4, 1))
    match_score = match_expr.label("match_score")

    # ---------- Build query ----------
    stmt = (
        select(
            Song.id,
            Song.first_line,
            SongThemes.content.label("themes"),
            match_score,
        )
        .join(SongThemes, SongThemes.id == SongThemeEmbeddings.song_themes_id)
        .join(SongLyrics, SongLyrics.id == SongThemes.song_lyrics_id)
        .join(Song, Song.id == SongLyrics.song_id)
    )

    # Apply min match_score
    if req.min_match_score is not None:
        stmt = stmt.where(match_expr >= req.min_match_score)

    # Order and apply upper limit
    stmt = stmt.order_by(match_score.desc())
    stmt = stmt.limit(req.top_k)

    results = db.execute(stmt).all()
    return results
