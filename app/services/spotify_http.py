from __future__ import annotations

import asyncio
from typing import Any, Optional

import aiohttp
from fastapi import HTTPException, status


async def spotify_request_json(
    session: aiohttp.ClientSession,
    *,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    timeout: int = 20,
    max_retries: int = 3,
    context: str = "Spotify request",
) -> dict[str, Any]:
    """
    Execute a Spotify HTTP request with explicit 429 handling.

    Retries on:
    - 429 (using Retry-After if present)
    - transient 5xx errors
    """

    last_status: Optional[int] = None
    last_data: Any = None

    for attempt in range(max_retries + 1):
        async with session.request(
            method,
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
        ) as response:
            payload = await response.json(content_type=None)

            if response.status < 400:
                return payload

            last_status = response.status
            last_data = payload

            should_retry = response.status == 429 or response.status >= 500
            if not should_retry or attempt == max_retries:
                break

            retry_after_raw = response.headers.get("Retry-After")
            if retry_after_raw and retry_after_raw.isdigit():
                delay = float(retry_after_raw)
            else:
                delay = 0.8 * (2**attempt)

            await asyncio.sleep(max(0.5, min(delay, 10.0)))

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"{context} failed (status={last_status})",
    )
