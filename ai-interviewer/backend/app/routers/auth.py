"""Auth API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    GoogleLoginRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    TokenResponse,
    UserInfo,
)
from app.services.auth_service import AuthService, get_auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Login with Google",
    description="Verify Google id_token, create or find user, return JWT.",
)
async def google_login(
    request: GoogleLoginRequest,
    session: AsyncSession = Depends(get_session),
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate with Google and return a JWT."""
    try:
        google_info = auth.verify_google_token(request.credential)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    user = await auth.get_or_create_user(session, google_info)
    access_token = auth.create_access_token(user.id, user.email)
    await session.commit()

    return TokenResponse(
        access_token=access_token,
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        profile_completed=user.profile_completed,
        is_admin=user.is_admin,
    )


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Get current user info",
)
async def get_me(
    user: User = Depends(get_current_user),
) -> UserInfo:
    """Return current user info from JWT."""
    return UserInfo(
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        sex=user.sex,
        age=user.age,
        profile_completed=user.profile_completed,
        is_admin=user.is_admin,
    )


@router.put(
    "/profile",
    response_model=ProfileResponse,
    summary="Update user profile",
    description="Update name, sex, age and mark profile as completed.",
)
async def update_profile(
    request: ProfileUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    """Update user profile fields."""
    user.display_name = request.display_name
    user.sex = request.sex
    user.age = request.age
    user.profile_completed = True

    await session.commit()
    await session.refresh(user)

    return ProfileResponse(
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        sex=user.sex,
        age=user.age,
        profile_completed=user.profile_completed,
        is_admin=user.is_admin,
    )
