from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Song, SongLyrics, SongUsage, UserRole, User
from app.schemas.songs import (
    SongListFilters,
    SongBasicDetails,
    SongFullDetails,
    SongUsageSchema,
    SongUsageFilters
)
from app.dependencies import require_min_role

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
    if filter_query.is_hymn is not None:
        query = query.filter(Song.is_hymn == filter_query.is_hymn)
    if filter_query.added_after is not None:
        query = query.filter(Song.created_on >= filter_query.added_after)
    if filter_query.added_before is not None:
        query = query.filter(Song.created_on <= filter_query.added_before)
    if filter_query.lyrics is not None:
        query = query.join(SongLyrics).filter(
            SongLyrics.content.ilike(f"%{filter_query.lyrics}%")
        )
    if filter_query.last_used_after is not None:
        query = query.filter(Song.last_used >= filter_query.last_used_after)
    if filter_query.last_used_before is not None:
        query = query.filter(Song.last_used <= filter_query.last_used_before)
    if filter_query.used_at is not None:
        # distinct is not strictly necessary when using last_used column property
        # in Song model
        query = (
            query.join(SongUsage)
            .filter(SongUsage.used_at.in_(filter_query.used_at))
            .distinct()
        )

    return query.all()


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
    if filters.used_at:
        query = query.filter(SongUsage.used_at.in_(filters.used_at))

    return query.all()
