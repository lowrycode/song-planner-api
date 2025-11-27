from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Song, SongLyrics, SongUsage, UserRole, User
from app.schemas.songs import SongListFilters, SongBasicDetails
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
        query = query.join(SongUsage).filter(
            SongUsage.used_at.in_(filter_query.used_at)
        ).distinct()

    return query.all()
