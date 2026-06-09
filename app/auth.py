import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request, status

from app.config import Settings, get_settings

SESSION_ACCESS_TOKEN = "access_token"
SESSION_REFRESH_TOKEN = "refresh_token"
SESSION_EXPIRES_AT = "expires_at"
SESSION_OAUTH_STATE = "oauth_state"


def build_authorize_url(settings: Settings, state: str) -> str:
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": settings.spotify_scopes,
        "state": state,
        "show_dialog": "false",
    }
    return f"{settings.spotify_auth_url}?{urlencode(params)}"


def create_oauth_state(request: Request) -> str:
    state = secrets.token_urlsafe(32)
    request.session[SESSION_OAUTH_STATE] = state
    return state


def validate_oauth_state(request: Request, state: str) -> None:
    expected = request.session.pop(SESSION_OAUTH_STATE, None)
    if not expected or not secrets.compare_digest(expected, state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state parameter.",
        )


async def exchange_code_for_tokens(
    settings: Settings, code: str
) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.spotify_token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.spotify_redirect_uri,
            },
            auth=(settings.spotify_client_id, settings.spotify_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code for tokens.",
        )

    return response.json()


def store_tokens(request: Request, token_payload: dict[str, Any]) -> None:
    expires_in = int(token_payload.get("expires_in", 3600))
    request.session[SESSION_ACCESS_TOKEN] = token_payload["access_token"]
    request.session[SESSION_REFRESH_TOKEN] = token_payload.get("refresh_token")
    request.session[SESSION_EXPIRES_AT] = time.time() + expires_in - 30


def clear_session(request: Request) -> None:
    request.session.clear()


def is_authenticated(request: Request) -> bool:
    return bool(request.session.get(SESSION_ACCESS_TOKEN))


async def get_valid_access_token(request: Request) -> str:
    settings = get_settings()
    access_token = request.session.get(SESSION_ACCESS_TOKEN)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Visit /auth/login first.",
        )

    expires_at = request.session.get(SESSION_EXPIRES_AT, 0)
    if time.time() < expires_at:
        return access_token

    refresh_token = request.session.get(SESSION_REFRESH_TOKEN)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Visit /auth/login to re-authenticate.",
        )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.spotify_token_url,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            auth=(settings.spotify_client_id, settings.spotify_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != status.HTTP_200_OK:
        clear_session(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh access token. Visit /auth/login.",
        )

    payload = response.json()
    store_tokens(
        request,
        {
            **payload,
            "refresh_token": payload.get("refresh_token", refresh_token),
        },
    )
    return request.session[SESSION_ACCESS_TOKEN]
