from datetime import date
from pydantic import BaseModel, HttpUrl, ConfigDict
from enum import Enum


# Enums
class SongType(str, Enum):
    song = "song"
    hymn = "hymn"


# Dependency Schemas
class SongLyricsSchema(BaseModel):
    content: str
    model_config = ConfigDict(from_attributes=True)


class SongResourcesSchema(BaseModel):
    sheet_music: HttpUrl | None = None
    harmony_vid: HttpUrl | None = None
    harmony_pdf: HttpUrl | None = None
    harmony_ms: HttpUrl | None = None
    model_config = ConfigDict(from_attributes=True)


class ActivityUsageStats(BaseModel):
    id: int
    name: str
    usage_count: int
    first_used: date | None = None
    last_used: date | None = None
    model_config = ConfigDict(from_attributes=True)


class OverallActivityUsageStats(BaseModel):
    usage_count: int
    first_used: date | None
    last_used: date | None
    model_config = ConfigDict(from_attributes=True)


# Filter Query Schemas
class SongListFilters(BaseModel):
    song_key: str | None = None
    song_type: SongType | None = None
    lyric: str | None = None


class SongKeyFilters(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    church_activity_id: list[int] | None = None
    unique: bool = False


class SongTypeFilters(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    church_activity_id: list[int] | None = None
    unique: bool = False


class SongUsageFilters(BaseModel):
    used_after: date | None = None
    used_before: date | None = None
    church_activity_id: list[int] | None = None


class SongListUsageFilters(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    lyric: str | None = None
    song_key: str | None = None
    song_type: SongType | None = None
    last_used_in_range: bool = False
    first_used_in_range: bool = False
    church_activity_id: list[int] | None = None


# Response Schemas
class SongBasicDetails(BaseModel):
    id: int
    first_line: str
    model_config = ConfigDict(from_attributes=True)


class SongTypeResponse(BaseModel):
    hymn: int
    song: int
    model_config = ConfigDict(from_attributes=True)


class SongFullDetails(BaseModel):
    id: int
    first_line: str
    song_key: str
    is_hymn: bool
    copyright: str | None = None
    author: str | None = None
    duration: int | None = None
    lyrics: SongLyricsSchema
    resources: SongResourcesSchema
    model_config = ConfigDict(from_attributes=True)


class SongUsageSchema(BaseModel):
    id: int
    used_date: date
    church_activity_id: int
    model_config = ConfigDict(from_attributes=True)


class SongListUsageResponse(BaseModel):
    id: int
    first_line: str
    activities: dict[str, ActivityUsageStats]
    overall: OverallActivityUsageStats
    model_config = ConfigDict(from_attributes=True)