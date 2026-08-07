from __future__ import annotations

from datetime import datetime, timedelta

from bson import ObjectId

from app.db.mongo import PROMPTS_LOG_TTL_DAYS, get_collections

cols = get_collections()
prompts_col = cols["prompts"]


class PromptsRepo:
    async def create_generation_log(
        self,
        *,
        user_id: str,
        prompt: str,
        min_songs: int,
        max_songs: int,
        response_songs: list[dict],
    ) -> dict:
        now = datetime.utcnow()
        expires_at = now + timedelta(days=PROMPTS_LOG_TTL_DAYS)

        doc = {
            "user_id": ObjectId(user_id),
            "prompt": prompt,
            "request": {
                "min_songs": min_songs,
                "max_songs": max_songs,
            },
            "response": {
                "songs": response_songs,
                "total_songs": len(response_songs),
            },
            "created_at": now,
            "updated_at": now,
            "expires_at": expires_at,
        }
        res = await prompts_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def delete_by_user(self, user_id: str) -> int:
        res = await prompts_col.delete_many({"user_id": ObjectId(user_id)})
        return int(res.deleted_count)
