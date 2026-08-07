import hashlib
import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jwt import InvalidTokenError, decode, encode
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRES_MIN", "60"))
TOKEN_ISSUER = os.getenv("JWT_ISSUER", "aura-cue-api")
TOKEN_AUDIENCE = os.getenv("JWT_AUDIENCE", "aura-cue-web")

if not SECRET_KEY or len(SECRET_KEY.encode("utf-8")) < 32:
    raise RuntimeError("JWT_SECRET must contain at least 32 bytes")

if not 1 <= ACCESS_TOKEN_EXPIRE_MINUTES <= 1440:
    raise RuntimeError("JWT_EXPIRES_MIN must be between 1 and 1440")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _prehash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return pwd_context.hash(_prehash(password))


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_prehash(password), hashed_password)


def create_access_token(*, sub: str, auth_version: int = 0) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "ver": auth_version,
        "iss": TOKEN_ISSUER,
        "aud": TOKEN_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=TOKEN_AUDIENCE,
            issuer=TOKEN_ISSUER,
        )
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
