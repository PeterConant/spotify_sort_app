from typing import Any

from fastapi import APIRouter, Query, Request

from app.auth import get_valid_access_token
from app.spotify import SpotifyClient

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/spotify/me/playlists")
async def debug_spotify_list_playlists(
    request: Request,
    limit: int = Query(default=50, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Return the raw JSON from Spotify's GET /me/playlists endpoint."""
    access_token = await get_valid_access_token(request)
    client = SpotifyClient(access_token)
    return await client.get_raw(
        "/me/playlists",
        params={"limit": limit, "offset": offset},
    )


@router.get("/spotify/playlists/{playlist_id}/items")
async def debug_spotify_get_playlist_items(
    request: Request,
    playlist_id: str,
    limit: int = Query(default=50, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Return the raw JSON from Spotify's GET /playlists/{id}/items endpoint."""
    access_token = await get_valid_access_token(request)
    client = SpotifyClient(access_token)
    return await client.get_raw(
        f"/playlists/{playlist_id}/items",
        params={"limit": limit, "offset": offset},
    )


@router.get("/spotify/playlists/{playlist_id}")
async def debug_spotify_get_playlist(
    request: Request,
    playlist_id: str,
) -> dict[str, Any]:
    """Return the raw JSON from Spotify's GET /playlists/{id} endpoint."""
    access_token = await get_valid_access_token(request)
    client = SpotifyClient(access_token)
    return await client.get_raw(f"/playlists/{playlist_id}")
