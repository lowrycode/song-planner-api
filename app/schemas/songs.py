from datetime import datetime
from pydantic import BaseModel, HttpUrl, ConfigDict


class SongUsage(BaseModel):
    used_date: datetime
    used_at: str


class SongBasicDetails(BaseModel):
    id: int
    first_line: str
    song_key: str
    is_hymn: bool
    created_on: datetime
    last_used: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SongFullDetails(BaseModel):
    song_id: int
    first_line: str
    song_key: str
    is_hymn: bool
    copyright: str | None = None
    author: str | None = None
    duration: int | None = None
    created_on: datetime
    lyrics: str
    usage: list[SongUsage]
    sheet_music: HttpUrl
    harmony_video: HttpUrl | None = None
    harmony_pdf: HttpUrl | None = None
    harmony_ms: HttpUrl | None = None


class SongListFilters(BaseModel):
    song_key: str | None = None
    is_hymn: bool | None = None
    added_after: datetime | None = None
    added_before: datetime | None = None
    lyrics: str | None = None
    last_used_after: datetime | None = None
    last_used_before: datetime | None = None
    used_at: list[str] | None = None
