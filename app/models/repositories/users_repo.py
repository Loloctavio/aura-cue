from datetime import datetime

from bson import ObjectId
from pymongo.collation import Collation
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument

from app.db.mongo import get_collections

cols = get_collections()
users_col = cols["users"]
EMAIL_COLLATION = Collation(locale="en", strength=2)


def _object_id(value: str) -> ObjectId | None:
    return ObjectId(value) if ObjectId.is_valid(value) else None


class UsersRepo:
    async def create(self, *, username: str, gmail: str, hashed_password: str, profile_photo: str | None):
        now = datetime.utcnow()
        existing = await users_col.find_one({"gmail": gmail}, collation=EMAIL_COLLATION)
        if existing:
            return None, "Gmail already exists"

        doc = {
            "username": username,
            "gmail": gmail,
            "password": hashed_password,
            "profile_photo": profile_photo,
            "playlists": [],
            "spotify_connected": False,
            "auth_version": 0,
            "created_at": now,
            "updated_at": now,
        }
        try:
            res = await users_col.insert_one(doc)
        except DuplicateKeyError:
            return None, "Gmail already exists"
        doc["_id"] = res.inserted_id
        return doc, None

    async def get(self, user_id: str):
        object_id = _object_id(user_id)
        return await users_col.find_one({"_id": object_id}) if object_id else None

    async def find_by_gmail(self, gmail: str):
        return await users_col.find_one({"gmail": gmail}, collation=EMAIL_COLLATION)

    async def find_by_spotify_oauth_state(self, state: str):
        return await users_col.find_one({"spotify_oauth_state": state})

    async def consume_spotify_oauth_state(self, state: str, *, now: datetime):
        return await users_col.find_one_and_update(
            {
                "spotify_oauth_state": state,
                "spotify_oauth_state_expires_at": {"$gt": now},
            },
            {
                "$unset": {
                    "spotify_oauth_state": "",
                    "spotify_oauth_state_expires_at": "",
                }
            },
            return_document=ReturnDocument.BEFORE,
        )

    async def update(self, user_id: str, updates: dict):
        object_id = _object_id(user_id)
        if not object_id:
            return None
        updates["updated_at"] = datetime.utcnow()
        await users_col.update_one({"_id": object_id}, {"$set": updates})
        return await self.get(user_id)

    async def disconnect_spotify(self, user_id: str):
        object_id = _object_id(user_id)
        if not object_id:
            return None
        await users_col.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "spotify_connected": False,
                    "updated_at": datetime.utcnow(),
                },
                "$unset": {
                    "spotify": "",
                    "spotify_oauth_state": "",
                    "spotify_oauth_state_expires_at": "",
                    "spotify_oauth_redirect_to": "",
                },
            },
        )
        return await self.get(user_id)

    async def delete(self, user_id: str) -> bool:
        object_id = _object_id(user_id)
        if not object_id:
            return False
        res = await users_col.delete_one({"_id": object_id})
        return res.deleted_count > 0

    async def add_playlist(self, user_id: str, playlist_id: str):
        user_object_id = _object_id(user_id)
        playlist_object_id = _object_id(playlist_id)
        if not user_object_id or not playlist_object_id:
            return
        await users_col.update_one(
            {"_id": user_object_id},
            {"$addToSet": {"playlists": playlist_object_id}, "$set": {"updated_at": datetime.utcnow()}},
        )

    async def remove_playlist(self, user_id: str, playlist_id: str):
        user_object_id = _object_id(user_id)
        playlist_object_id = _object_id(playlist_id)
        if not user_object_id or not playlist_object_id:
            return
        await users_col.update_one(
            {"_id": user_object_id},
            {"$pull": {"playlists": playlist_object_id}, "$set": {"updated_at": datetime.utcnow()}},
        )
