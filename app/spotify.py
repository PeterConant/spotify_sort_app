from typing import Any

import httpx
from fastapi import HTTPException, status

from app.config import Settings, get_settings
from app.models import PlaylistSummary, TrackSummary

TRACK_FIELDS = (
    "items(added_at,track(type,id,name,uri,duration_ms,popularity,"
    "artists(name),album(name,release_date))),total,next"
)


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
            raise HTTPException(status_code=response.status_code, detail=detail)

        if not response.content:
            return {}
        return response.json()

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
                        track_count=item["tracks"]["total"],
                        snapshot_id=item.get("snapshot_id"),
                    )
                )

            if payload.get("next") is None:
                break
            offset += limit

        return playlists

    async def get_playlist(self, playlist_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/playlists/{playlist_id}")

    async def get_playlist_tracks(self, playlist_id: str) -> list[TrackSummary]:
        tracks: list[TrackSummary] = []
        offset = 0
        limit = 100

        while True:
            payload = await self._request(
                "GET",
                f"/playlists/{playlist_id}/tracks",
                params={"limit": limit, "offset": offset, "fields": TRACK_FIELDS},
            )

            for item in payload.get("items", []):
                track = item.get("track")
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
                        added_at=item.get("added_at"),
                        popularity=track.get("popularity"),
                        release_date=album.get("release_date"),
                    )
                )

            if payload.get("next") is None:
                break
            offset += limit

        return tracks

    async def _clear_playlist_tracks(self, playlist_id: str) -> None:
        offset = 0
        limit = 100

        while True:
            payload = await self._request(
                "GET",
                f"/playlists/{playlist_id}/tracks",
                params={"limit": limit, "offset": offset, "fields": "items(track(uri)),total,next"},
            )
            items = payload.get("items", [])
            if not items:
                break

            tracks_to_remove = [
                {"uri": item["track"]["uri"]}
                for item in items
                if item.get("track") and item["track"].get("uri")
            ]
            if tracks_to_remove:
                await self._request(
                    "DELETE",
                    f"/playlists/{playlist_id}/tracks",
                    json={"tracks": tracks_to_remove},
                )

            if payload.get("next") is None:
                break
            offset += limit

    async def apply_sorted_tracks(self, playlist_id: str, uris: list[str]) -> None:
        current_tracks = await self.get_playlist_tracks(playlist_id)
        current_uris = [track.uri for track in current_tracks]

        if current_uris == uris:
            return

        if len(uris) <= 100 and len(current_uris) <= 100:
            await self._request(
                "PUT",
                f"/playlists/{playlist_id}/tracks",
                json={"uris": uris},
            )
            return

        await self._clear_playlist_tracks(playlist_id)
        for index in range(0, len(uris), 100):
            await self._request(
                "POST",
                f"/playlists/{playlist_id}/tracks",
                json={"uris": uris[index : index + 100]},
            )
