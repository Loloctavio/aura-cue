import os
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.mongo import close_mongo, ensure_indexes, ping
from app.routes.playlists_routes import router as playlists_router
from app.routes.spotify_routes import router as spotify_router
from app.routes.user_routes import router as users_router
from app.security import SecurityMiddleware


def _cors_origin(value: str) -> str:
    origin = value.strip().rstrip("/")
    parsed = urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
        raise RuntimeError(f"Invalid CORS origin: {value!r}")
    return origin


environment = os.getenv("ENVIRONMENT", "development").lower()
docs_enabled = environment not in {"production", "prod"}
app = FastAPI(
    title="AI Playlist API",
    version="0.1.0",
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)

frontend_url = _cors_origin(os.getenv("FRONTEND_URL", "http://localhost:5173"))
extra_origins = [x.strip() for x in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if x.strip()]
allow_origins = list(dict.fromkeys([frontend_url, *(_cors_origin(origin) for origin in extra_origins)]))

app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(users_router)
app.include_router(playlists_router)
app.include_router(spotify_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
async def _startup():
    await ping()
    await ensure_indexes()


@app.on_event("shutdown")
def _shutdown():
    close_mongo()
