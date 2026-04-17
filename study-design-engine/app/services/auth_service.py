import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

# Reusable transport for Google token verification
_google_request = google_requests.Request()

# bcrypt caps inputs at 72 bytes. We truncate before hashing (rather than
# rejecting longer passwords) so the policy matches between hash() and verify().
_BCRYPT_MAX_BYTES = 72


def verify_google_token(token: str) -> dict:
    """Verify a Google ID token and return the payload."""
    payload = id_token.verify_oauth2_token(
        token,
        _google_request,
        settings.GOOGLE_CLIENT_ID,
    )
    return payload


async def get_or_create_user(google_payload: dict, db: AsyncSession) -> User:
    """Find existing user by google_sub, or create a new one.

    Enforces the ALLOWED_EMAILS allowlist BEFORE creating any user row: if the
    email isn't in the allowlist (and the allowlist is non-empty), we raise 403
    with no database side-effects, so rejected users don't leave ghost rows.
    An empty allowlist means allow-all (dev default).
    """
    sub = google_payload["sub"]
    email = google_payload.get("email", "")
    name = google_payload.get("name")
    picture = google_payload.get("picture")

    # Allowlist gate — applied to both new and returning sign-ins so that
    # removing an email from the list revokes access at next login.
    allowlist = settings.allowed_emails_set
    if allowlist and email.strip().lower() not in allowlist:
        logger.warning("Rejected sign-in for non-allowlisted email: %s", email)
        raise HTTPException(
            status_code=403,
            detail="This email isn't approved for the beta. Contact the admin to request access.",
        )

    result = await db.execute(select(User).where(User.google_sub == sub))
    user = result.scalar_one_or_none()

    if user:
        user.last_login_at = datetime.now(timezone.utc)
        if name:
            user.name = name
        if picture:
            user.picture_url = picture
        await db.commit()
        await db.refresh(user)
        return user

    user = User(
        email=email,
        name=name,
        picture_url=picture,
        google_sub=sub,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Created new user: %s (%s)", email, user.id)
    return user


def _prepare_bcrypt_input(plain: str) -> bytes:
    """Encode a password for bcrypt, truncating at 72 bytes (bcrypt's hard limit).

    Using a consistent truncation in both hash + verify keeps behavior identical
    regardless of input length — no surprising rejections for long passwords.
    """
    return plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain: str) -> str:
    """Hash a password for storage. Uses bcrypt (cost factor 12)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(_prepare_bcrypt_input(plain), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time verify of a candidate password against a stored hash."""
    try:
        return bcrypt.checkpw(_prepare_bcrypt_input(plain), hashed.encode("utf-8"))
    except Exception:
        return False


async def authenticate_with_password(
    username: str,
    password: str,
    db: AsyncSession,
) -> Optional[User]:
    """Look up a user by username and verify the password. None on any failure.

    Always runs the bcrypt verify step even when the user is missing — this
    keeps the response-time footprint identical whether the username exists or
    not, blocking username-enumeration via timing. The dummy hash below is a
    valid bcrypt hash for a random string, so `verify` takes the full ~200ms.
    """
    _DUMMY_HASH = "$2b$12$CpJZx5ZBL6Kp8oVhfN7rRe7bqTq9kW.Y6jGxGqKqKqKqKqKqKqKqK"

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not user.password_hash:
        verify_password(password, _DUMMY_HASH)
        return None

    if not verify_password(password, user.password_hash):
        return None

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


def create_jwt(user: User) -> str:
    """Create a JWT for the given user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": now + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
