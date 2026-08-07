from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.models.repositories.users_repo import UsersRepo
from app.services.auth_service import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    repo = UsersRepo()
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if payload.get("ver", 0) != user.get("auth_version", 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is no longer valid")

    spotify_doc = user.get("spotify") or {}
    spotify_public = None
    if user.get("spotify_connected"):
        spotify_public = {
            "spotify_user_id": spotify_doc.get("spotify_user_id"),
            "expires_at": spotify_doc.get("expires_at"),
            "connected_at": spotify_doc.get("connected_at"),
        }

    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "gmail": user["gmail"],
        "profile_photo": user.get("profile_photo"),
        "playlists": [str(x) for x in user.get("playlists", [])],
        "spotify_connected": bool(user.get("spotify_connected", False)),
        "spotify": spotify_public,
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }
