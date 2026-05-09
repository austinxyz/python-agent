"""Authentication service: password hashing, email canonicalization, Google
ID token verification.

Per multi-user-auth-core spec.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Email canonicalization (invariant: every read & write goes through this)
# ---------------------------------------------------------------------------


def canonicalize_email(email: str) -> str:
    """Lowercase + trim. Use for every users.email read or write.

    `Austin@Gmail.com` and `austin@gmail.com` resolve to the same row;
    leading / trailing whitespace is rejected from storage.
    """
    if email is None:
        return ""
    return email.strip().lower()


# ---------------------------------------------------------------------------
# Password hashing (argon2id)
# ---------------------------------------------------------------------------

_argon2_hasher = None


def _hasher():
    global _argon2_hasher
    if _argon2_hasher is None:
        from argon2 import PasswordHasher

        _argon2_hasher = PasswordHasher()
    return _argon2_hasher


def hash_password(plaintext: str) -> str:
    """Hash a password with argon2id (defaults). Returns the encoded string
    starting with $argon2id$. Plaintext is never logged.
    """
    if not plaintext:
        raise ValueError("password must be non-empty")
    return _hasher().hash(plaintext)


def verify_password(stored_hash: str, plaintext: str) -> bool:
    """Verify plaintext against an argon2id hash. False on any mismatch
    (including malformed hash, wrong password, expired hash). Never raises
    on a normal mismatch.
    """
    if not stored_hash or not plaintext:
        return False
    try:
        from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

        return _hasher().verify(stored_hash, plaintext)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Google ID token verification
# ---------------------------------------------------------------------------


def verify_google_token(id_token: str, audience: str | None = None) -> dict[str, Any]:
    """Verify a Google-issued ID token JWT. Returns the claims dict on
    success. Raises ValueError on any verification failure (signature,
    expiry, audience mismatch).

    `audience` defaults to GOOGLE_CLIENT_ID env var.
    """
    if not id_token:
        raise ValueError("id_token is required")
    aud = audience or os.environ.get("GOOGLE_CLIENT_ID", "")
    if not aud:
        raise ValueError("GOOGLE_CLIENT_ID not configured")

    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as gid_token

    try:
        claims = gid_token.verify_oauth2_token(
            id_token, google_requests.Request(), aud
        )
    except Exception as e:
        # Re-raise as ValueError with sanitized message — never leak full token
        raise ValueError(f"google token verification failed: {type(e).__name__}") from e
    return claims
