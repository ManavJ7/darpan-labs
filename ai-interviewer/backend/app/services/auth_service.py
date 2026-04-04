"""Authentication service for Google OAuth + JWT."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


class AuthService:
    """Handles Google token verification, JWT creation, and user management."""

    def verify_google_token(self, credential: str) -> dict:
        """Verify a Google id_token and return user info.

        Args:
            credential: The Google id_token string.

        Returns:
            Dict with sub, email, name, picture from Google.

        Raises:
            ValueError: If token is invalid.
        """
        try:
            idinfo = google_id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.google_client_id,
            )
            return {
                "sub": idinfo["sub"],
                "email": idinfo["email"],
                "name": idinfo.get("name", ""),
                "picture": idinfo.get("picture", ""),
            }
        except Exception as e:
            logger.error(f"Google token verification failed: {e}")
            raise ValueError(f"Invalid Google token: {e}")

    async def get_or_create_user(
        self, session: AsyncSession, google_info: dict
    ) -> User:
        """Find existing user by email or create a new one.

        Args:
            session: Database session.
            google_info: Dict from verify_google_token.

        Returns:
            User instance.
        """
        result = await session.execute(
            select(User).where(User.email == google_info["email"])
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                email=google_info["email"],
                display_name=google_info["name"] or google_info["email"].split("@")[0],
                auth_provider_id=google_info["sub"],
            )
            session.add(user)
            await session.flush()
            logger.info(f"Created new user {user.id} for {user.email}")
        else:
            # Update auth_provider_id if not set
            if not user.auth_provider_id:
                user.auth_provider_id = google_info["sub"]
                await session.flush()

        return user

    def create_access_token(self, user_id: UUID, email: str) -> str:
        """Create a JWT access token.

        Args:
            user_id: User UUID.
            email: User email.

        Returns:
            Encoded JWT string.
        """
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.auth_access_token_expire_minutes
        )
        payload = {
            "sub": str(user_id),
            "email": email,
            "exp": expire,
        }
        return jwt.encode(
            payload,
            settings.auth_secret_key,
            algorithm=settings.auth_algorithm,
        )

    def decode_token(self, token: str) -> dict:
        """Decode and validate a JWT token.

        Args:
            token: JWT string.

        Returns:
            Dict with sub, email from the token.

        Raises:
            ValueError: If token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                settings.auth_secret_key,
                algorithms=[settings.auth_algorithm],
            )
            user_id = payload.get("sub")
            email = payload.get("email")
            if user_id is None:
                raise ValueError("Invalid token: missing sub")
            return {"sub": user_id, "email": email}
        except JWTError as e:
            raise ValueError(f"Invalid token: {e}")

    async def get_user_by_id(self, session: AsyncSession, user_id: UUID) -> User | None:
        """Look up a user by ID.

        Args:
            session: Database session.
            user_id: User UUID.

        Returns:
            User or None.
        """
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


def get_auth_service() -> AuthService:
    """Get auth service instance."""
    return AuthService()
