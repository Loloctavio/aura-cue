from fastapi import APIRouter, Depends
from app.controllers.users_controller import UsersController
from app.models.user_schemas import (
    UserRegister,
    UserLogin,
    UserUpdate,
    ChangePassword,
    TokenResponse,
    UserOut,
)
from app.services.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["users"])
controller = UsersController()


def _serialize_user(doc: dict) -> dict:
    spotify_doc = doc.get("spotify") or {}
    spotify_public = None
    if doc.get("spotify_connected"):
        spotify_public = {
            "spotify_user_id": spotify_doc.get("spotify_user_id"),
            "expires_at": spotify_doc.get("expires_at"),
            "connected_at": spotify_doc.get("connected_at"),
        }

    return {
        "id": str(doc["_id"]),
        "username": doc["username"],
        "gmail": doc["gmail"],
        "profile_photo": doc.get("profile_photo"),
        "playlists": [str(x) for x in doc.get("playlists", [])],
        "spotify_connected": bool(doc.get("spotify_connected", False)),
        "spotify": spotify_public,
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


@router.post("/register", response_model=TokenResponse)
async def register(payload: UserRegister):
    return await controller.register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    return await controller.login(payload)


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
async def update_me(payload: UserUpdate, current_user=Depends(get_current_user)):
    doc = await controller.update_me(current_user, payload)
    return _serialize_user(doc)


@router.put("/me/password", response_model=TokenResponse)
async def change_password(payload: ChangePassword, current_user=Depends(get_current_user)):
    return await controller.change_password(current_user, payload)


@router.delete("/me")
async def delete_me(current_user=Depends(get_current_user)):
    return await controller.delete_me(current_user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: str, current_user=Depends(get_current_user)):
    doc = await controller.get_by_id(current_user, user_id)
    return _serialize_user(doc)
