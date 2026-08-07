from __future__ import annotations

import os
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.controllers.spotify_controller import SpotifyController
from app.services.dependencies import get_current_user

router = APIRouter(tags=["spotify"])
controller = SpotifyController()


def _frontend_profile_url() -> str:
    frontend_base = os.getenv("FRONTEND_URL")
    return f"{frontend_base}/profile"


def _with_status(url: str, *, status_value: str, message: str | None = None) -> str:
    sep = "&" if "?" in url else "?"
    params = {"spotify": status_value}
    if message:
        params["message"] = message
    return f"{url}{sep}{urlencode(params)}"


@router.get("/spotify/connect")
async def spotify_connect(
    redirect_to: str | None = Query(default=None, max_length=200),
    as_redirect: bool = Query(default=False),
    current_user=Depends(get_current_user),
):
    payload = await controller.start_connect(
        user_id=current_user["id"],
        redirect_to=redirect_to,
    )

    if as_redirect:
        return RedirectResponse(payload["authorization_url"], status_code=307)

    return payload


@router.delete("/spotify/disconnect")
async def spotify_disconnect(current_user=Depends(get_current_user)):
    return await controller.disconnect(user_id=current_user["id"])


async def _handle_spotify_callback(
    code: str | None = Query(default=None, max_length=2048),
    state: str | None = Query(default=None, max_length=200),
    error: str | None = Query(default=None, max_length=100),
):
    target = _frontend_profile_url()

    if error:
        return RedirectResponse(_with_status(target, status_value="error", message=error), status_code=307)

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    result = await controller.handle_callback(code=code, state=state)

    redirect_to = result.get("redirect_to")
    if isinstance(redirect_to, str) and redirect_to.strip():
        if redirect_to.startswith("/"):
            frontend_base = os.getenv("FRONTEND_URL").rstrip("/")
            target = f"{frontend_base}{redirect_to}"

    return RedirectResponse(_with_status(target, status_value="connected"), status_code=307)


@router.get("/spotify/callback")
async def spotify_callback(
    code: str | None = Query(default=None, max_length=2048),
    state: str | None = Query(default=None, max_length=200),
    error: str | None = Query(default=None, max_length=100),
):
    return await _handle_spotify_callback(code=code, state=state, error=error)


@router.get("/callback")
async def spotify_callback_legacy(
    code: str | None = Query(default=None, max_length=2048),
    state: str | None = Query(default=None, max_length=200),
    error: str | None = Query(default=None, max_length=100),
):
    return await _handle_spotify_callback(code=code, state=state, error=error)
