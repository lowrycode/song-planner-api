from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement
from app.models import Song, SongLyrics, SongUsage, SongUsageStats
from app.schemas.songs import SongType

MIN_USAGE_DATE = date(1900, 1, 1)
MAX_USAGE_DATE = date(2100, 1, 1)


def get_effective_activity_ids(
    allowed_activity_ids: set[int],
    filter_activity_ids: set[int] | None,
) -> set[int]:
    """Returns activity IDs to filter by, restricted to user-permitted activities."""
    if not filter_activity_ids:
        return allowed_activity_ids

    return allowed_activity_ids & filter_activity_ids


def build_song_usage_filters(
    effective_activity_ids: set[int], from_date: date | None, to_date: date | None
) -> list[ColumnElement]:
    """
    Builds SQLAlchemy filters for SongUsage based on activity scope and date range.
    Defaults to full date range when bounds are not provided.
    """
    from_date = from_date or MIN_USAGE_DATE
    to_date = to_date or MAX_USAGE_DATE

    return [
        SongUsage.church_activity_id.in_(effective_activity_ids),
        SongUsage.used_date.between(from_date, to_date),
    ]


def build_song_usage_stats_filters(
    effective_activity_ids: set[int],
    from_date: date | None,
    to_date: date | None,
    first_used_in_range: bool,
    last_used_in_range: bool,
) -> list[ColumnElement]:
    """
    Builds SQLAlchemy filters for SongUsageStats using activity scope,
    and optional first/last usage range filters.
    """
    from_date = from_date or MIN_USAGE_DATE
    to_date = to_date or MAX_USAGE_DATE

    filters = [SongUsageStats.church_activity_id.in_(effective_activity_ids)]
    if first_used_in_range:
        filters.append(SongUsageStats.first_used.between(from_date, to_date))
    if last_used_in_range:
        filters.append(SongUsageStats.last_used.between(from_date, to_date))

    return filters


def build_song_filters(
    db: Session,
    song_key: str | None,
    song_type: SongType | None = None,
    lyric: str | None = None,
) -> list[ColumnElement]:
    """
    Builds SQLAlchemy filters for querying Songs based on key, type, and lyric content.
    """

    filters = []
    if song_key:
        filters.append(Song.song_key == song_key)
    if song_type:
        if song_type == SongType.song:
            filters.append(Song.is_hymn.is_(False))
        elif song_type == SongType.hymn:
            filters.append(Song.is_hymn.is_(True))
    if lyric:
        lyrics_subquery = (
            db.query(SongLyrics.id)
            .filter(
                SongLyrics.song_id == Song.id,
                SongLyrics.content.ilike(f"%{lyric}%"),
            )
            .exists()
        )
        filters.append(lyrics_subquery)

    return filters
