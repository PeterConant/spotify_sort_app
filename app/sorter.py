from app.models import SortField, SortOrder, TrackSummary


def _sort_key(track: TrackSummary, field: SortField):
    if field == SortField.NAME:
        return track.name.casefold()
    if field == SortField.ARTIST:
        return track.artist.casefold()
    if field == SortField.ALBUM:
        return track.album.casefold()
    if field == SortField.DURATION:
        return track.duration_ms
    if field == SortField.ADDED_AT:
        return track.added_at or ""
    if field == SortField.POPULARITY:
        return track.popularity if track.popularity is not None else -1
    if field == SortField.RELEASE_DATE:
        return track.release_date or ""
    return track.name.casefold()


def sort_tracks(
    tracks: list[TrackSummary],
    *,
    by: SortField,
    order: SortOrder,
) -> list[TrackSummary]:
    reverse = order == SortOrder.DESC
    return sorted(tracks, key=lambda track: _sort_key(track, by), reverse=reverse)
