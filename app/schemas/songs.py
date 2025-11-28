from datetime import datetime
from pydantic import BaseModel, HttpUrl, ConfigDict


class SongUsageSchema(BaseModel):
    id: int
    used_date: datetime
    used_at: str
    model_config = ConfigDict(from_attributes=True)


class SongBasicDetails(BaseModel):
    id: int
    first_line: str
    song_key: str
    is_hymn: bool
    created_on: datetime
    last_used: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class SongLyricsSchema(BaseModel):
    content: str
    model_config = ConfigDict(from_attributes=True)


class SongResourcesSchema(BaseModel):
    sheet_music: HttpUrl | None = None
    harmony_vid: HttpUrl | None = None
    harmony_pdf: HttpUrl | None = None
    harmony_ms: HttpUrl | None = None
    model_config = ConfigDict(from_attributes=True)


class SongFullDetails(BaseModel):
    id: int
    first_line: str
    song_key: str
    is_hymn: bool
    copyright: str | None = None
    author: str | None = None
    duration: int | None = None
    created_on: datetime
    last_used: datetime | None = None
    lyrics: SongLyricsSchema
    resources: SongResourcesSchema
    model_config = ConfigDict(from_attributes=True)


class SongUsageList(BaseModel):
    id: int
    usages: list[SongUsageSchema]
    model_config = ConfigDict(from_attributes=True)


class SongListFilters(BaseModel):
    song_key: str | None = None
    is_hymn: bool | None = None
    added_after: datetime | None = None
    added_before: datetime | None = None
    lyrics: str | None = None
    last_used_after: datetime | None = None
    last_used_before: datetime | None = None
    used_at: list[str] | None = None
