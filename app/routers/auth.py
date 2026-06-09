from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from app.auth import (
    build_authorize_url,
    clear_session,
    create_oauth_state,
    exchange_code_for_tokens,
    get_valid_access_token,
    is_authenticated,
    store_tokens,
    validate_oauth_state,
)
from app.config import get_settings
from app.models import AuthStatus
from app.spotify import SpotifyClient

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    settings = get_settings()
    state = create_oauth_state(request)
    return RedirectResponse(build_authorize_url(settings, state))


@router.get("/callback")
async def callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    validate_oauth_state(request, state)
    settings = get_settings()
    token_payload = await exchange_code_for_tokens(settings, code)
    store_tokens(request, token_payload)
    return RedirectResponse(url="/docs")


@router.get("/logout")
async def logout(request: Request) -> dict[str, str]:
    clear_session(request)
    return {"message": "Logged out."}


@router.get("/me", response_model=AuthStatus)
async def me(request: Request) -> AuthStatus:
    if not is_authenticated(request):
        return AuthStatus(authenticated=False)

    access_token = await get_valid_access_token(request)
    client = SpotifyClient(access_token)
    user = await client.get_current_user()
    return AuthStatus(
        authenticated=True,
        display_name=user.get("display_name"),
        user_id=user.get("id"),
    )
