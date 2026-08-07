import asyncio
import unittest

from pydantic import ValidationError

from app.models.playlist_schemas import PlaylistGenerateRequest, PlaylistSaveRequest, VerifiedMeta
from app.models.user_schemas import UserRegister
from app.security import RateLimit, _FixedWindowLimiter
from app.services.auth_service import create_access_token, decode_token
from app.services.token_crypto import decrypt_secret, encrypt_secret


class SecuritySchemaTests(unittest.TestCase):
    def test_prompt_is_bounded_and_not_blank(self):
        self.assertEqual(PlaylistGenerateRequest(prompt="  jazz  ").prompt, "jazz")
        for invalid in ("   ", "x" * 1001):
            with self.assertRaises(ValidationError):
                PlaylistGenerateRequest(prompt=invalid)

    def test_spotify_url_rejects_script_and_lookalike_hosts(self):
        invalid_urls = (
            "javascript:alert(1)",
            "https://example.com/track/abc",
            "https://open.spotify.com.evil.test/track/abc",
        )
        for invalid in invalid_urls:
            with self.assertRaises(ValidationError):
                VerifiedMeta(spotify_url=invalid)

        result = VerifiedMeta(spotify_url="https://open.spotify.com/track/abc123")
        self.assertEqual(result.spotify_url, "https://open.spotify.com/track/abc123")

    def test_playlist_and_password_inputs_are_bounded(self):
        with self.assertRaises(ValidationError):
            PlaylistSaveRequest(name="x", songs=[{"artist": "a", "track": "t"}] * 201)

        with self.assertRaises(ValidationError):
            UserRegister(username="tester", gmail="test@example.com", password="short")


class SecurityServiceTests(unittest.TestCase):
    def test_jwt_contains_auth_version(self):
        token = create_access_token(sub="507f1f77bcf86cd799439011", auth_version=3)
        self.assertEqual(decode_token(token)["ver"], 3)

    def test_spotify_credentials_are_encrypted(self):
        encrypted = encrypt_secret("spotify-token")
        self.assertNotEqual(encrypted, "spotify-token")
        self.assertEqual(decrypt_secret(encrypted), "spotify-token")

    def test_rate_limiter_blocks_after_limit(self):
        async def exercise():
            limiter = _FixedWindowLimiter()
            limit = RateLimit(requests=2, window_seconds=60)
            self.assertIsNone(await limiter.consume("client", limit))
            self.assertIsNone(await limiter.consume("client", limit))
            self.assertIsNotNone(await limiter.consume("client", limit))

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
