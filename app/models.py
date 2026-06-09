from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SortField(str, Enum):
    NAME = "name"
    ARTIST = "artist"
    ALBUM = "album"
    DURATION = "duration"
    ADDED_AT = "added_at"
    POPULARITY = "popularity"
    RELEASE_DATE = "release_date"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortRequest(BaseModel):
    by: SortField = SortField.NAME
    order: SortOrder = SortOrder.ASC
    dry_run: bool = Field(
        default=False,
        description="When true, returns the sorted track list without modifying the playlist.",
    )


class TrackSummary(BaseModel):
    uri: str
    name: str
    artist: str
    album: str
    duration_ms: int
    added_at: str | None = None
    popularity: int | None = None
    release_date: str | None = None


class SortResponse(BaseModel):
    playlist_id: str
    playlist_name: str
    sort_by: SortField
    order: SortOrder
    dry_run: bool
    track_count: int
    tracks: list[TrackSummary]
    applied: bool


class PlaylistSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    owner: str
    public: bool
    collaborative: bool
    snapshot_id: str | None = None


class AuthStatus(BaseModel):
    authenticated: bool
    display_name: str | None = None
    user_id: str | None = None


class ErrorResponse(BaseModel):
    detail: str
    extra: dict[str, Any] | None = None
