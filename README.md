# Spotify Playlist Sorter

A FastAPI service that sorts your Spotify playlists by track name, artist, album, duration, date added, popularity, or release date.

## Prerequisites

1. A [Spotify Developer account](https://developer.spotify.com/dashboard)
2. A registered app with redirect URI: `http://127.0.0.1:8000/auth/callback`
3. Python 3.11+

## Setup

```bash
cd Projects/spotify-playlist-sorter
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with your Spotify client credentials and a random `SESSION_SECRET`.

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for interactive API docs.

## Authentication

1. Visit `GET /auth/login` in your browser to authorize with Spotify.
2. After redirect, your session cookie is set automatically.
3. Use `GET /auth/me` to verify authentication.

## API overview

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /auth/login` | Start Spotify OAuth |
| `GET /auth/me` | Current auth status |
| `GET /auth/logout` | Clear session |
| `GET /playlists` | List your playlists |
| `GET /playlists/{id}` | Playlist details |
| `POST /playlists/{id}/sort` | Sort a playlist |

## Sort a playlist

Preview without modifying:

```json
POST /playlists/{playlist_id}/sort
{
  "by": "artist",
  "order": "asc",
  "dry_run": true
}
```

Apply the sort:

```json
POST /playlists/{playlist_id}/sort
{
  "by": "release_date",
  "order": "desc",
  "dry_run": false
}
```

### Sort fields

- `name` — track title
- `artist` — primary artist
- `album` — album name
- `duration` — track length (ms)
- `added_at` — when the track was added to the playlist
- `popularity` — Spotify popularity score
- `release_date` — album release date

### Sort order

- `asc` — ascending
- `desc` — descending

## Notes

- Only track items are sorted; podcast episodes and other non-track entries are skipped.
- You can only sort playlists **you own** or **collaborative playlists** — followed playlists owned by others will return 403.
- Spotify's 2026 API uses `/playlists/{id}/items` (not `/tracks`). If you previously authenticated, visit `/auth/logout` then `/auth/login` again after updating.
- Large playlists are rewritten in batches of 100 tracks per Spotify API limits.
- Use `dry_run: true` first to preview the new order before applying changes.
- The `popularity` sort field may return identical values — Spotify removed popularity from playlist item responses in 2026.
