from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str = "http://127.0.0.1:8000/auth/callback"
    session_secret: str
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    spotify_auth_url: str = "https://accounts.spotify.com/authorize"
    spotify_token_url: str = "https://accounts.spotify.com/api/token"
    spotify_api_base: str = "https://api.spotify.com/v1"

    spotify_scopes: str = " ".join(
        [
            "playlist-read-private",
            "playlist-read-collaborative",
            "playlist-modify-public",
            "playlist-modify-private",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
