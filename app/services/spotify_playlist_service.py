from __future__ import annotations

import base64
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import aiohttp
from fastapi import HTTPException, status

from app.models.repositories.users_repo import UsersRepo
from app.services.spotify_http import spotify_request_json
from app.services.token_crypto import decrypt_secret, encrypt_secret


class SpotifyPlaylistService:
    def __init__(self) -> None:
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Missing Spotify client env vars")

        self.users_repo = UsersRepo()

    @staticmethod
    def _track_uri_from_song(song: dict) -> str | None:
        verified = song.get("verified") if isinstance(song, dict) else None
        spotify_id = None

        if isinstance(verified, dict):
            spotify_id = verified.get("spotify_id")
        if not spotify_id:
            spotify_id = song.get("spotify_id") if isinstance(song, dict) else None

        if spotify_id and isinstance(spotify_id, str):
            return f"spotify:track:{spotify_id}"
        return None

    async def _refresh_access_token(self, refresh_token: str) -> dict:
        credentials = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        basic = base64.b64encode(credentials).decode("utf-8")

        headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        body = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        async with aiohttp.ClientSession() as session:
            return await spotify_request_json(
                session,
                method="POST",
                url="https://accounts.spotify.com/api/token",
                headers=headers,
                data=body,
                timeout=20,
                context="Spotify refresh",
            )

    async def _store_encrypted_tokens(
        self,
        *,
        user_doc: dict,
        spotify: dict,
        access_token: str,
        refresh_token: str | None,
    ) -> None:
        spotify["access_token_enc"] = encrypt_secret(access_token)
        spotify["refresh_token_enc"] = encrypt_secret(refresh_token)
        spotify.pop("access_token", None)
        spotify.pop("refresh_token", None)
        await self.users_repo.update(str(user_doc["_id"]), {"spotify": spotify, "spotify_connected": True})

    async def _get_valid_access_token(self, user_doc: dict) -> str:
        spotify = user_doc.get("spotify") or {}
        access_token = decrypt_secret(spotify.get("access_token_enc")) or spotify.get("access_token")
        refresh_token = decrypt_secret(spotify.get("refresh_token_enc")) or spotify.get("refresh_token")
        expires_at = spotify.get("expires_at")
        uses_legacy_plaintext = bool(access_token and not spotify.get("access_token_enc"))

        if access_token and isinstance(expires_at, datetime) and expires_at > datetime.utcnow() + timedelta(seconds=30):
            if uses_legacy_plaintext:
                await self._store_encrypted_tokens(
                    user_doc=user_doc,
                    spotify=spotify,
                    access_token=access_token,
                    refresh_token=refresh_token,
                )
            return access_token

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Spotify access expired and no refresh token available",
            )

        refreshed = await self._refresh_access_token(refresh_token)
        new_access_token = refreshed.get("access_token")
        if not new_access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not refresh Spotify token")

        expires_in = max(1, min(int(refreshed.get("expires_in", 3600)), 86_400))
        new_refresh = refreshed.get("refresh_token", refresh_token)

        spotify["expires_at"] = datetime.utcnow() + timedelta(seconds=expires_in)
        spotify["token_type"] = refreshed.get("token_type", spotify.get("token_type", "Bearer"))
        if refreshed.get("scope"):
            spotify["scope"] = refreshed.get("scope")

        await self._store_encrypted_tokens(
            user_doc=user_doc,
            spotify=spotify,
            access_token=new_access_token,
            refresh_token=new_refresh,
        )
        return new_access_token

    async def _create_playlist(
        self,
        *,
        access_token: str,
        spotify_user_id: str,
        name: str,
        description: str | None,
        public: bool,
    ) -> dict:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "name": name,
            "description": description or "Created from SayPlay",
            "public": public,
        }

        async with aiohttp.ClientSession() as session:
            return await spotify_request_json(
                session,
                method="POST",
                url=f"https://api.spotify.com/v1/users/{spotify_user_id}/playlists",
                headers=headers,
                json=payload,
                timeout=20,
                context="Spotify create playlist",
            )

    async def _add_tracks(self, *, access_token: str, playlist_id: str, uris: List[str]) -> None:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(uris), 100):
                chunk = uris[i : i + 100]
                await spotify_request_json(
                    session,
                    method="POST",
                    url=f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                    headers=headers,
                    json={"uris": chunk},
                    timeout=20,
                    context="Spotify add tracks",
                )

    async def export_playlist(self, *, user_doc: dict, playlist_doc: dict, public: bool = False) -> Dict[str, Any]:
        if not user_doc.get("spotify_connected"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Spotify account not connected")

        spotify_doc = user_doc.get("spotify") or {}
        spotify_user_id = spotify_doc.get("spotify_user_id")
        if not spotify_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Spotify user id not found")

        songs = playlist_doc.get("songs") or []
        uris = [uri for uri in (self._track_uri_from_song(song) for song in songs) if uri]
        uris = list(dict.fromkeys(uris))

        if not uris:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No Spotify-track matches to export")

        access_token = await self._get_valid_access_token(user_doc)

        created = await self._create_playlist(
            access_token=access_token,
            spotify_user_id=spotify_user_id,
            name=playlist_doc.get("name") or "SayPlay Playlist",
            description=playlist_doc.get("description") or "Created from SayPlay",
            public=public,
        )

        playlist_id = created.get("id")
        if not playlist_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Spotify did not return playlist id")

        await self._add_tracks(access_token=access_token, playlist_id=playlist_id, uris=uris)

        return {
            "exported": True,
            "spotify_playlist_id": playlist_id,
            "spotify_playlist_url": (created.get("external_urls") or {}).get("spotify"),
            "added_tracks": len(uris),
            "total_songs": len(songs),
        }
