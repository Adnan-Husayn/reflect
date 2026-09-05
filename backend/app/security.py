"""Password hashing, session signing and cookie handling.

The session cookie is signed and HttpOnly. JavaScript cannot read it, so an XSS
bug cannot exfiltrate a session — which matters more here than in a typical
project, because the account holds PHQ-8 responses.
"""

import time
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Response
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from app.config import get_settings

SESSION_COOKIE = "reflect_session"

_hasher = PasswordHasher()

# Rate limiting is per-process and in-memory: it survives neither a restart nor
# a second worker. Enough to blunt casual guessing in a demo, and the README
# says so rather than implying otherwise.
MAX_ATTEMPTS = 8
COOLDOWN_SECONDS = 300
_attempts: dict[str, tuple[int, float]] = {}


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Verify a password against a stored hash.

    A null hash never verifies. The seeded development user has one, which is
    what makes that account unreachable once registration exists.
    """
    if not password_hash:
        return False
    try:
        _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False
    return True


def _signer() -> TimestampSigner:
    return TimestampSigner(get_settings().secret_key)


def sign_user_id(user_id: str) -> str:
    return _signer().sign(user_id).decode()


def unsign_user_id(token: str) -> str | None:
    """Return the user id, or None if the token is tampered with or expired."""
    max_age = get_settings().session_max_age_days * 24 * 60 * 60
    try:
        return _signer().unsign(token, max_age=max_age).decode()
    except (BadSignature, SignatureExpired):
        return None


def set_session_cookie(response: Response, user_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        sign_user_id(user_id),
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.session_max_age_days * 24 * 60 * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="lax")


# ── login throttling ──────────────────────────────────────────────────


@dataclass(frozen=True)
class Throttle:
    blocked: bool
    seconds_remaining: int


def check_throttle(key: str, now: float | None = None) -> Throttle:
    now = time.time() if now is None else now
    count, first_seen = _attempts.get(key, (0, now))
    if now - first_seen > COOLDOWN_SECONDS:
        return Throttle(blocked=False, seconds_remaining=0)
    if count >= MAX_ATTEMPTS:
        return Throttle(blocked=True, seconds_remaining=int(COOLDOWN_SECONDS - (now - first_seen)))
    return Throttle(blocked=False, seconds_remaining=0)


def record_failure(key: str, now: float | None = None) -> None:
    now = time.time() if now is None else now
    count, first_seen = _attempts.get(key, (0, now))
    if now - first_seen > COOLDOWN_SECONDS:
        count, first_seen = 0, now
    _attempts[key] = (count + 1, first_seen)


def clear_failures(key: str) -> None:
    _attempts.pop(key, None)
