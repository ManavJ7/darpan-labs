"""FastAPI dependency for extracting the current authenticated user from JWT."""

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.study import Study
from app.models.user import User
from app.services.auth_service import decode_jwt


async def _user_from_header(request: Request, db: AsyncSession) -> Optional[User]:
    """Shared JWT-decode path. Returns None for any missing/invalid token case.

    Used by both `get_current_user` (which raises on None) and
    `get_current_user_optional` (which doesn't). Keeps token-decode logic in
    one place.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_jwt(token)
    except Exception:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        return None

    result = await db.execute(select(User).where(User.id == uid))
    return result.scalar_one_or_none()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    """Extract and validate JWT from Authorization header, return the User."""
    user = await _user_from_header(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """Like `get_current_user` but returns None instead of raising.

    Use this on GET endpoints that should be accessible to anonymous visitors
    when the target resource is public (`Study.is_public = True`). Callers
    decide the policy.
    """
    return await _user_from_header(request, db)


async def require_study_owner(
    study_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Study:
    """Load a study and assert `current_user` can mutate it. Raises on failure.

    Policy:
    - Public studies are frozen demos — no one can mutate them, including the
      original owner. This protects the seeded Dove studies from accidental
      or malicious re-simulation (each run is ~$60 in LLM spend). Raises 403.
    - Unclaimed legacy studies (created_by_user_id IS NULL): the first
      authenticated mutation claims ownership.
    - Otherwise: the caller must be the owner.

    Reads use `ensure_readable_study` instead, which permits any auth user on
    a private study and any visitor on a public one.
    """
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    if getattr(study, "is_public", False):
        raise HTTPException(
            status_code=403,
            detail="This is a public demo study and cannot be modified. Create your own to run simulations.",
        )

    owner_id = getattr(study, "created_by_user_id", None)
    if owner_id is None:
        study.created_by_user_id = current_user.id
        return study

    if owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to modify this study.",
        )
    return study


async def ensure_readable_study(
    study_id: uuid.UUID,
    current_user: Optional[User],
    db: AsyncSession,
) -> Study:
    """Load a study for read access. Raises 404 or 401 as appropriate.

    Read policy:
    - Public study → anyone (auth or anon) can read
    - Private study → any authenticated user can read (shared-read across
      logged-in users; ownership only gates writes)

    Use this in GET endpoints that should participate in the public demo flow.
    """
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    if getattr(study, "is_public", False):
        return study

    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return study
