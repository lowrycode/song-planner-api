from datetime import date
from app.models import SongUsage, SongUsageStats
from sqlalchemy.sql.elements import ColumnElement

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
