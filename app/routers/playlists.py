from fastapi import APIRouter, Request

from app.auth import get_valid_access_token
from app.models import PlaylistSummary, SortRequest, SortResponse
from app.sorter import sort_tracks
from app.spotify import SpotifyClient

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.get("", response_model=list[PlaylistSummary])
async def list_playlists(request: Request) -> list[PlaylistSummary]:
    access_token = await get_valid_access_token(request)
    client = SpotifyClient(access_token)
    return await client.list_playlists()


@router.get("/{playlist_id}", response_model=PlaylistSummary)
async def get_playlist(request: Request, playlist_id: str) -> PlaylistSummary:
    access_token = await get_valid_access_token(request)
    client = SpotifyClient(access_token)
    payload = await client.get_playlist(playlist_id)
    return PlaylistSummary(
        id=payload["id"],
        name=payload["name"],
        description=payload.get("description"),
        owner=payload["owner"]["display_name"] or payload["owner"]["id"],
        public=bool(payload.get("public")),
        collaborative=bool(payload.get("collaborative")),
        track_count=payload["tracks"]["total"],
        snapshot_id=payload.get("snapshot_id"),
    )


@router.post("/{playlist_id}/sort", response_model=SortResponse)
async def sort_playlist(
    request: Request,
    playlist_id: str,
    body: SortRequest,
) -> SortResponse:
    access_token = await get_valid_access_token(request)
    client = SpotifyClient(access_token)

    playlist = await client.get_playlist(playlist_id)
    tracks = await client.get_playlist_tracks(playlist_id)
    sorted_tracks = sort_tracks(tracks, by=body.by, order=body.order)

    applied = False
    if not body.dry_run:
        await client.apply_sorted_tracks(
            playlist_id, [track.uri for track in sorted_tracks]
        )
        applied = True

    return SortResponse(
        playlist_id=playlist_id,
        playlist_name=playlist["name"],
        sort_by=body.by,
        order=body.order,
        dry_run=body.dry_run,
        track_count=len(sorted_tracks),
        tracks=sorted_tracks,
        applied=applied,
    )
