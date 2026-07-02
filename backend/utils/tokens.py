"""
Shared token mechanics for the password_tokens flows (invite + reset).

Kept in utils/ so both usuarios.py (invite-on-create) and the password router
generate and hash tokens identically — no drift.

Security properties:
  - Generation: secrets.token_urlsafe(32) → 256 bits of URL-safe entropy.
  - Storage: only the sha256 hex of the raw token is persisted (token_hash).
    The raw token travels only in the email link and is never logged/stored.
  - Expiry is applied in SQL (NOW() + INTERVAL) using the TTL constants below,
    so the database clock is the single source of truth.
"""

import hashlib
import secrets

# TTLs live here as SQL INTERVAL literals so callers interpolate them directly
# into `expires_at = NOW() + INTERVAL '...'` (never from user input).
INVITE_TTL_SQL = "72 hours"
RESET_TTL_SQL = "1 hour"


def generate_raw_token() -> str:
    """Return a fresh URL-safe raw token (never stored — only its hash is)."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """Return the sha256 hex digest stored in password_tokens.token_hash."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
