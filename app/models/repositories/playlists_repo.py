from datetime import datetime

from bson import ObjectId

from app.db.mongo import get_collections

cols = get_collections()
playlists_col = cols["playlists"]


def _object_id(value: str) -> ObjectId | None:
    return ObjectId(value) if ObjectId.is_valid(value) else None


class PlaylistsRepo:
    async def create(
        self,
        user_id: ObjectId,
        name: str,
        description: str | None,
        songs: list[dict],
        source_prompt: str | None,
        total_songs: int,
        total_duration_ms: int | None,
    ):
        now = datetime.utcnow()
        doc = {
            "user_id": user_id,
            "name": name,
            "description": description,
            "source_prompt": source_prompt,
            "songs": songs,
            "total_songs": total_songs,
            "total_duration_ms": total_duration_ms,
            "created_at": now,
            "updated_at": now,
        }
        res = await playlists_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def get(self, playlist_id: str):
        object_id = _object_id(playlist_id)
        return await playlists_col.find_one({"_id": object_id}) if object_id else None

    async def list_by_user(self, user_id: str, limit: int = 50, skip: int = 0):
        object_id = _object_id(user_id)
        if not object_id:
            return []
        cursor = playlists_col.find({"user_id": object_id}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def update(self, playlist_id: str, updates: dict):
        object_id = _object_id(playlist_id)
        if not object_id:
            return None
        updates["updated_at"] = datetime.utcnow()
        await playlists_col.update_one({"_id": object_id}, {"$set": updates})
        return await self.get(playlist_id)

    async def delete(self, playlist_id: str):
        object_id = _object_id(playlist_id)
        if not object_id:
            return False
        res = await playlists_col.delete_one({"_id": object_id})
        return res.deleted_count > 0

    async def delete_by_user(self, user_id: str) -> int:
        object_id = _object_id(user_id)
        if not object_id:
            return 0
        res = await playlists_col.delete_many({"user_id": object_id})
        return int(res.deleted_count)
