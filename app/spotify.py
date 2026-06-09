from typing import Any

import httpx
from fastapi import HTTPException, status

from app.config import Settings, get_settings
from app.models import PlaylistSummary, TrackSummary

PLAYLIST_ITEMS_BATCH = 100
PLAYLIST_ITEMS_PAGE = 50

ITEM_FIELDS = (
    "items(added_at,item(type,id,name,uri,duration_ms,"
    "artists(name),album(name,release_date))),total,next"
)


def _entry_track(entry: dict[str, Any]) -> dict[str, Any] | None:
    return entry.get("item") or entry.get("track")


def _playlist_items_path(playlist_id: str) -> str:
    return f"/playlists/{playlist_id}/items"


class SpotifyClient:
    def __init__(self, access_token: str, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.settings.spotify_api_base}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers=self.headers,
                params=params,
                json=json,
            )

        if response.status_code == status.HTTP_204_NO_CONTENT:
            return {}

        if response.status_code >= 400:
            detail = "Spotify API request failed."
            try:
                payload = response.json()
                if isinstance(payload, dict) and "error" in payload:
                    error = payload["error"]
                    if isinstance(error, dict):
                        detail = error.get("message", detail)
                    else:
                        detail = str(error)
            except ValueError:
                pass

            if response.status_code == status.HTTP_403_FORBIDDEN:
                detail = (
                    f"{detail} You can only read or modify playlists you own or "
                    "collaborate on. Followed playlists owned by other users are "
                    "not supported."
                )

            raise HTTPException(status_code=response.status_code, detail=detail)

        if not response.content:
            return {}
        return response.json()

    async def get_raw(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def get_current_user(self) -> dict[str, Any]:
        return await self._request("GET", "/me")

    async def list_playlists(self, limit: int = 50) -> list[PlaylistSummary]:
        playlists: list[PlaylistSummary] = []
        offset = 0

        while True:
            payload = await self._request(
                "GET",
                "/me/playlists",
                params={"limit": limit, "offset": offset},
            )
            for item in payload.get("items", []):
                playlists.append(
                    PlaylistSummary(
                        id=item["id"],
                        name=item["name"],
                        description=item.get("description"),
                        owner=item["owner"]["display_name"] or item["owner"]["id"],
                        public=bool(item.get("public")),
                        collaborative=bool(item.get("collaborative")),
                        snapshot_id=item.get("snapshot_id"),
                    )
                )

            if payload.get("next") is None:
                break
            offset += limit

        return playlists

    async def get_playlist(self, playlist_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/playlists/{playlist_id}")

    async def ensure_playlist_modifiable(
        self, playlist_id: str, current_user_id: str
    ) -> dict[str, Any]:
        playlist = await self.get_playlist(playlist_id)
        owner_id = playlist["owner"]["id"]
        if owner_id != current_user_id and not playlist.get("collaborative"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "This playlist belongs to another user. Only playlists you "
                    "own or collaborate on can be sorted."
                ),
            )
        return playlist

    async def get_playlist_tracks(self, playlist_id: str) -> list[TrackSummary]:
        tracks: list[TrackSummary] = []
        offset = 0
        items_path = _playlist_items_path(playlist_id)

        while True:
            payload = await self._request(
                "GET",
                items_path,
                params={
                    "limit": PLAYLIST_ITEMS_PAGE,
                    "offset": offset,
                    "fields": ITEM_FIELDS,
                },
            )

            for entry in payload.get("items", []):
                track = _entry_track(entry)
                if not track or track.get("type") != "track" or not track.get("uri"):
                    continue

                artists = track.get("artists") or []
                album = track.get("album") or {}
                tracks.append(
                    TrackSummary(
                        uri=track["uri"],
                        name=track.get("name") or "Unknown",
                        artist=(
                            artists[0].get("name") if artists else "Unknown Artist"
                        ),
                        album=album.get("name") or "Unknown Album",
                        duration_ms=int(track.get("duration_ms") or 0),
                        added_at=entry.get("added_at"),
                        popularity=track.get("popularity"),
                        release_date=album.get("release_date"),
                    )
                )

            if payload.get("next") is None:
                break
            offset += PLAYLIST_ITEMS_PAGE

        return tracks

    async def _clear_playlist_items(self, playlist_id: str) -> None:
        items_path = _playlist_items_path(playlist_id)

        while True:
            payload = await self._request(
                "GET",
                items_path,
                params={
                    "limit": PLAYLIST_ITEMS_PAGE,
                    "offset": 0,
                    "fields": "items(item(uri),track(uri)),total,next",
                },
            )
            entries = payload.get("items", [])
            if not entries:
                break

            items_to_remove = []
            for entry in entries:
                track = _entry_track(entry)
                if track and track.get("uri"):
                    items_to_remove.append({"uri": track["uri"]})

            if not items_to_remove:
                break

            await self._request(
                "DELETE",
                items_path,
                json={"items": items_to_remove},
            )

    async def apply_sorted_tracks(self, playlist_id: str, uris: list[str]) -> None:
        current_tracks = await self.get_playlist_tracks(playlist_id)
        current_uris = [track.uri for track in current_tracks]

        if current_uris == uris:
            return

        items_path = _playlist_items_path(playlist_id)

        if len(uris) <= PLAYLIST_ITEMS_BATCH and len(current_uris) <= PLAYLIST_ITEMS_BATCH:
            await self._request(
                "PUT",
                items_path,
                json={"uris": uris},
            )
            return

        await self._clear_playlist_items(playlist_id)
        for index in range(0, len(uris), PLAYLIST_ITEMS_BATCH):
            await self._request(
                "POST",
                items_path,
                json={"uris": uris[index : index + PLAYLIST_ITEMS_BATCH]},
            )
