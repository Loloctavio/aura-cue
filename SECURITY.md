# Security and production checklist

Report suspected vulnerabilities privately to the repository owner. Do not include
credentials, access tokens, personal data, or exploit payloads in public issues.

## Required deployment settings

- Set ENVIRONMENT=production to disable the API documentation endpoints.
- Generate JWT_SECRET from at least 32 random bytes. Rotating it invalidates all sessions.
- Generate SPOTIFY_TOKEN_ENCRYPTION_KEY with Fernet.generate_key() and store it
  separately from MongoDB backups. Losing it makes stored Spotify credentials unusable.
- Use HTTPS URLs for FRONTEND_URL, SPOTIPY_REDIRECT_URI, and the frontend API URL.
- Keep CORS_ALLOW_ORIGINS limited to exact trusted frontend origins.
- Give the MongoDB user access only to this application's database and restrict Atlas
  network access to the backend deployment.
- Set request-size and request-rate limits at the load balancer or API gateway too.
  The application limiter is intentionally local to each process.
- Alert on repeated 401, 413, and 429 responses without logging passwords, JWTs,
  Spotify authorization codes, or Spotify credentials.

## Migration notes

Existing JWTs are invalid after this release because issuer/audience claims and a new
signing key are required. Existing plaintext Spotify credentials are encrypted and the
plaintext fields removed the next time that account exports a playlist. To remove them
immediately, ask connected users to disconnect and reconnect Spotify. Old database
backups may still contain plaintext credentials and must be protected or expired.

## Accepted residual risks

The SPA keeps its short-lived bearer token in sessionStorage. The CSP and external URL
allowlists reduce token-theft paths, but an HttpOnly cookie design would further reduce
impact from a future XSS and would require CSRF protection.

Rate limiting is in memory. Use a shared gateway or Redis-backed limiter before a
multi-instance or high-volume launch.

npm audit may flag React Router GHSA-qwww-vcr4-c8h2. This project is pinned to the
maintainer-patched 7.18.2 release and uses declarative browser routing, not the affected
unstable React Server Components APIs. Recheck this disposition on dependency updates.
