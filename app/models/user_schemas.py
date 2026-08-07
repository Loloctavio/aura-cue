from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    gmail: EmailStr
    password: str = Field(min_length=12, max_length=256)
    profile_photo: Optional[str] = Field(default=None, max_length=2048)

    @field_validator("username")
    @classmethod
    def username_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Username must contain at least 3 non-space characters")
        return value


class UserLogin(BaseModel):
    gmail: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=30)
    profile_photo: Optional[str] = Field(default=None, max_length=2048)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Username must contain at least 3 non-space characters")
        return value


class ChangePassword(BaseModel):
    old_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SpotifyInfoOut(BaseModel):
    spotify_user_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    connected_at: Optional[datetime] = None


class UserOut(BaseModel):
    id: str
    username: str
    gmail: EmailStr
    profile_photo: Optional[str] = None
    playlists: List[str] = Field(default_factory=list)
    spotify_connected: bool = False
    spotify: Optional[SpotifyInfoOut] = None
    created_at: datetime
    updated_at: datetime
