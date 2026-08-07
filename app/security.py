from __future__ import annotations

import asyncio
import hashlib
import os
import time
from dataclasses import dataclass

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


@dataclass(frozen=True)
class RateLimit:
    requests: int
    window_seconds: int


ROUTE_LIMITS: dict[tuple[str, str], RateLimit] = {
    ("POST", "/users/register"): RateLimit(requests=5, window_seconds=600),
    ("POST", "/users/login"): RateLimit(requests=10, window_seconds=300),
    ("POST", "/playlists/generate"): RateLimit(requests=6, window_seconds=600),
}


class _FixedWindowLimiter:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, int]] = {}
        self._lock = asyncio.Lock()

    async def consume(self, key: str, limit: RateLimit) -> int | None:
        now = time.monotonic()
        async with self._lock:
            started_at, count = self._entries.get(key, (now, 0))
            if now - started_at >= limit.window_seconds:
                started_at, count = now, 0

            if count >= limit.requests:
                return max(1, int(limit.window_seconds - (now - started_at)))

            self._entries[key] = (started_at, count + 1)

            if len(self._entries) > 10_000:
                cutoff = now - max(item.window_seconds for item in ROUTE_LIMITS.values())
                self._entries = {
                    entry_key: value
                    for entry_key, value in self._entries.items()
                    if value[0] >= cutoff
                }

        return None


def _request_identity(scope: Scope) -> str:
    client = scope.get("client")
    client_ip = client[0] if client else "unknown"
    authorization = Headers(scope=scope).get("authorization", "")
    if authorization.lower().startswith("bearer "):
        token_digest = hashlib.sha256(authorization.encode("utf-8")).hexdigest()[:24]
        return f"{client_ip}:{token_digest}"
    return client_ip


class SecurityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.limiter = _FixedWindowLimiter()
        self.rate_limits_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() not in {"0", "false", "no"}
        self.max_request_bytes = int(os.getenv("MAX_REQUEST_BYTES", "1000000"))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > self.max_request_bytes:
            response = JSONResponse({"detail": "Request body is too large."}, status_code=413)
            await response(scope, receive, send)
            return

        route_key = (scope["method"].upper(), scope["path"])
        limit = ROUTE_LIMITS.get(route_key) if self.rate_limits_enabled else None
        if limit:
            identity = _request_identity(scope)
            retry_after = await self.limiter.consume(f"{route_key}:{identity}", limit)
            if retry_after is not None:
                response = JSONResponse(
                    {"detail": "Too many requests. Please try again later."},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
                await response(scope, receive, send)
                return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                        (b"cache-control", b"no-store"),
                    ]
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
