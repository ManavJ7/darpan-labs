import uuid
import logging
from datetime import datetime, timezone, timedelta

import jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

# Reusable transport for Google token verification
_google_request = google_requests.Request()


def verify_google_token(token: str) -> dict:
    """Verify a Google ID token and return the payload."""
    payload = id_token.verify_oauth2_token(
        token,
        _google_request,
        settings.GOOGLE_CLIENT_ID,
    )
    return payload


async def get_or_create_user(google_payload: dict, db: AsyncSession) -> User:
    """Find existing user by google_sub, or create a new one."""
    sub = google_payload["sub"]
    email = google_payload.get("email", "")
    name = google_payload.get("name")
    picture = google_payload.get("picture")

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
