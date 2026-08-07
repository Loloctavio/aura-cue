import os

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()

_key = os.getenv("SPOTIFY_TOKEN_ENCRYPTION_KEY")
if not _key:
    raise RuntimeError("SPOTIFY_TOKEN_ENCRYPTION_KEY is not set")

try:
    _fernet = Fernet(_key.encode("ascii"))
except (ValueError, UnicodeEncodeError) as exc:
    raise RuntimeError("SPOTIFY_TOKEN_ENCRYPTION_KEY must be a valid Fernet key") from exc


def encrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return _fernet.decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError) as exc:
        raise RuntimeError("Stored Spotify credential could not be decrypted") from exc
