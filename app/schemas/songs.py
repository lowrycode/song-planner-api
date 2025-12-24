from datetime import date
from pydantic import BaseModel, HttpUrl, ConfigDict, field_validator
from enum import Enum


# Enums
class SongType(str, Enum):
    song = "song"
    hymn = "hymn"


# Shared Schemas
class UsageContextFilters(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    church_activity_id: list[int] | None = None


class SongLyricsSchema(BaseModel):
    content: str
    model_config = ConfigDict(from_attributes=True)


class SongResourcesSchema(BaseModel):
    sheet_music: HttpUrl | None = None
    harmony_vid: HttpUrl | None = None
    harmony_pdf: HttpUrl | None = None
    harmony_ms: HttpUrl | None = None

    @field_validator(
        "sheet_music",
        "harmony_vid",
        "harmony_pdf",
        "harmony_ms",
        mode="before",
    )
    def empty_str_to_none(cls, v):
        return v or None

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


class SongKeyFilters(UsageContextFilters):
    unique: bool = False


class SongTypeFilters(UsageContextFilters):
    unique: bool = False


class SongUsageFilters(UsageContextFilters):
    pass


class SongListUsageFilters(UsageContextFilters):
    song_key: str | None = None
    song_type: SongType | None = None
    lyric: str | None = None
    last_used_in_range: bool = False
    first_used_in_range: bool = False
    used_in_range: bool = False


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
