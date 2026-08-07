from fastapi import HTTPException

from app.models.repositories.playlists_repo import PlaylistsRepo
from app.models.repositories.prompts_repo import PromptsRepo
from app.models.repositories.users_repo import UsersRepo
from app.services.auth_service import create_access_token, hash_password, verify_password


class UsersController:
    def __init__(self):
        self.repo = UsersRepo()
        self.playlists_repo = PlaylistsRepo()
        self.prompts_repo = PromptsRepo()

    async def register(self, payload):
        hashed = hash_password(payload.password)
        doc, err = await self.repo.create(
            username=payload.username,
            gmail=str(payload.gmail).strip().lower(),
            hashed_password=hashed,
            profile_photo=payload.profile_photo,
        )
        if err:
            raise HTTPException(status_code=409, detail=err)

        token = create_access_token(sub=str(doc["_id"]), auth_version=doc.get("auth_version", 0))
        return {"access_token": token, "token_type": "bearer"}

    async def login(self, payload):
        user = await self.repo.find_by_gmail(str(payload.gmail).strip().lower())
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(payload.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token(sub=str(user["_id"]), auth_version=user.get("auth_version", 0))
        return {"access_token": token, "token_type": "bearer"}

    async def me(self, current_user: dict):
        return current_user

    async def update_me(self, current_user: dict, payload):
        updates = {}
        if payload.username is not None:
            updates["username"] = payload.username
        if payload.profile_photo is not None:
            updates["profile_photo"] = payload.profile_photo

        if not updates:
            return await self.repo.get(current_user["id"])

        return await self.repo.update(current_user["id"], updates)

    async def change_password(self, current_user: dict, payload):
        user = await self.repo.get(current_user["id"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(payload.old_password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        new_hashed = hash_password(payload.new_password)
        auth_version = user.get("auth_version", 0) + 1
        await self.repo.update(
            current_user["id"],
            {"password": new_hashed, "auth_version": auth_version},
        )
        token = create_access_token(sub=current_user["id"], auth_version=auth_version)
        return {"access_token": token, "token_type": "bearer"}

    async def delete_me(self, current_user: dict):
        user_id = current_user["id"]

        await self.playlists_repo.delete_by_user(user_id)
        await self.prompts_repo.delete_by_user(user_id)

        ok = await self.repo.delete(user_id)
        if not ok:
            raise HTTPException(status_code=404, detail="User not found")
        return {"deleted": True}

    async def get_by_id(self, current_user: dict, user_id: str):
        if user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden")

        user = await self.repo.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
