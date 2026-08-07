from __future__ import annotations

import logging
import os
from typing import Dict

import certifi
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.collation import Collation

load_dotenv()
logger = logging.getLogger(__name__)


def _clean_env(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value or None


MONGO_URI = _clean_env(os.getenv("MONGO_URI") or os.getenv("MONGODB_URI"))
MONGO_DB = _clean_env(os.getenv("MONGO_DB") or os.getenv("MONGODB_DB"))
PROMPTS_LOG_TTL_DAYS = max(1, int(_clean_env(os.getenv("PROMPTS_LOG_TTL_DAYS")) or "30"))

if not MONGO_URI:
    raise RuntimeError("MONGO_URI or MONGODB_URI is not set")

if not MONGO_URI.startswith(("mongodb://", "mongodb+srv://")):
    raise RuntimeError("Mongo URI must start with 'mongodb://' or 'mongodb+srv://'")

if not MONGO_DB:
    raise RuntimeError("MONGO_DB or MONGODB_DB is not set")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is not None:
        return _db

    _client = AsyncIOMotorClient(
        MONGO_URI,
        tls=True,
        tlsCAFile=certifi.where(),
        appname="ai-playlist",
    )

    _db = _client[MONGO_DB]
    return _db


def get_collection(name: str):
    return get_db()[name]


def get_collections() -> Dict[str, object]:
    db = get_db()
    return {
        "users": db["users"],
        "playlists": db["playlists"],
        "prompts": db["prompts"],
    }


async def ensure_indexes() -> None:
    db = get_db()
    indexes = (
        (
            db["users"],
            ("gmail",),
            {
                "unique": True,
                "collation": Collation(locale="en", strength=2),
                "name": "gmail_unique_ci",
            },
        ),
        (db["users"], ("spotify_oauth_state",), {"sparse": True}),
        (db["playlists"], ([("user_id", 1), ("created_at", -1)],), {}),
        (db["prompts"], ([("user_id", 1), ("created_at", -1)],), {}),
        (
            db["prompts"],
            ("expires_at",),
            {"expireAfterSeconds": 0, "name": f"prompts_ttl_{PROMPTS_LOG_TTL_DAYS}d"},
        ),
    )

    unique_collection, unique_args, unique_kwargs = indexes[0]
    try:
        await unique_collection.create_index(*unique_args, **unique_kwargs)
    except Exception as exc:
        raise RuntimeError("Could not enforce unique user emails") from exc

    for collection, args, kwargs in indexes[1:]:
        try:
            await collection.create_index(*args, **kwargs)
        except Exception as exc:
            logger.warning("Could not ensure non-critical MongoDB index %s", kwargs.get("name", args[0]))


async def ping() -> bool:
    await get_db().command("ping")
    return True


def close_mongo() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None
