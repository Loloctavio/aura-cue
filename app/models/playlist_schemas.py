from datetime import datetime
from typing import Annotated, List, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator

ShortLabel = Annotated[str, Field(min_length=1, max_length=100)]


class VerifiedMeta(BaseModel):
    status: str = Field(default="not_found", max_length=40)
    confidence: float = Field(default=0.0, ge=0, le=1)
    spotify_id: Optional[str] = Field(default=None, pattern=r"^[A-Za-z0-9]{1,64}$")
    spotify_url: Optional[str] = Field(default=None, max_length=2048)
    matched_track: Optional[str] = Field(default=None, max_length=300)
    matched_artist: Optional[str] = Field(default=None, max_length=200)
    preview_url: Optional[str] = Field(default=None, max_length=2048)

    @field_validator("spotify_url")
    @classmethod
    def validate_spotify_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "open.spotify.com"
            or parsed.username is not None
            or parsed.password is not None
            or not parsed.path.startswith("/track/")
        ):
            raise ValueError("spotify_url must be an HTTPS open.spotify.com track URL")
        return value


class Song(BaseModel):
    artist: str = Field(min_length=1, max_length=200)
    track: str = Field(min_length=1, max_length=300)
    reason: Optional[str] = Field(default=None, max_length=1000)
    genres: List[ShortLabel] = Field(default_factory=list, max_length=20)
    suggested_by: List[ShortLabel] = Field(default_factory=list, max_length=20)
    verified: Optional[VerifiedMeta] = None


class PlaylistGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)
    min_songs: int = Field(default=35, ge=1, le=200)
    max_songs: int = Field(default=50, ge=1, le=200)

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Prompt cannot be blank")
        return value


class PlaylistDraftOut(BaseModel):
    name_suggestion: str = "AI Playlist"
    description_suggestion: Optional[str] = None
    source_prompt: str
    songs: List[Song]
    total_songs: int


class PlaylistSaveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=400)
    songs: List[Song] = Field(default_factory=list, max_length=200)
    total_songs: Optional[int] = Field(default=None, ge=0, le=200)
    total_duration_ms: Optional[int] = Field(default=None, ge=0, le=86_400_000)
    source_prompt: Optional[str] = Field(default=None, max_length=1000)


class PlaylistUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=400)
    songs: Optional[List[Song]] = Field(default=None, max_length=200)
    total_songs: Optional[int] = Field(default=None, ge=0, le=200)
    total_duration_ms: Optional[int] = Field(default=None, ge=0, le=86_400_000)


class PlaylistOut(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    source_prompt: Optional[str] = None
    songs: List[Song]
    total_songs: int
    total_duration_ms: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class SpotifyExportRequest(BaseModel):
    public: bool = True


class SpotifyExportOut(BaseModel):
    exported: bool = True
    spotify_playlist_id: str
    spotify_playlist_url: Optional[str] = None
    added_tracks: int
    total_songs: int
