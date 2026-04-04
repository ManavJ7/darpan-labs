"""Authentication router — Google OAuth login and user info."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.user import User
from app.schemas.auth import AuthResponse, GoogleAuthRequest, UserResponse
from app.services.auth_service import create_jwt, get_or_create_user, verify_google_token

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/google", response_model=AuthResponse)
async def google_login(
    body: GoogleAuthRequest,
    db: AsyncSession = Depends(get_session),
):
    """Exchange a Google ID token for a JWT session token."""
    try:
        google_payload = verify_google_token(body.token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {exc}")

    user = await get_or_create_user(google_payload, db)
    access_token = create_jwt(user)

    return AuthResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            picture_url=user.picture_url,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture_url=current_user.picture_url,
    )


@router.post("/dev-login", response_model=AuthResponse)
async def dev_login(
    db: AsyncSession = Depends(get_session),
):
    """Dev-only login — bypasses Google OAuth. Creates/reuses a dev user."""
    from app.config import settings
    if settings.ENVIRONMENT not in ("development", "dev"):
        raise HTTPException(status_code=404, detail="Not found")

    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == "dev@darpan.local"))
    user = result.scalar_one_or_none()
    if not user:
        from sqlalchemy import text
        # Insert with all required columns for the unified users table
        await db.execute(text(
            "INSERT INTO users (id, email, display_name, name, google_sub) "
            "VALUES (:id, :email, :name, :name, :sub)"
        ), {"id": __import__("uuid").uuid4(), "email": "dev@darpan.local", "name": "Dev User", "sub": "dev-local"})
        await db.commit()
        result = await db.execute(select(User).where(User.email == "dev@darpan.local"))
        user = result.scalar_one()
        db.add(user)
        await db.commit()
        await db.refresh(user)

    access_token = create_jwt(user)
    return AuthResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            picture_url=user.picture_url,
        ),
    )
