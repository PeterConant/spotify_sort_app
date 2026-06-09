from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.routers import auth, debug, playlists


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings()
    yield


app = FastAPI(
    title="Spotify Playlist Sorter",
    description=(
        "API for sorting Spotify playlists by track name, artist, album, "
        "duration, date added, popularity, or release date."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="spotify_sorter_session",
    max_age=60 * 60 * 24 * 30,
    same_site="lax",
    https_only=False,
)

app.include_router(auth.router)
app.include_router(debug.router)
app.include_router(playlists.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
