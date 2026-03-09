"""Auth-related Pydantic schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class GoogleLoginRequest(BaseModel):
    """Request to login with Google."""

    credential: str = Field(..., description="Google id_token from frontend")


class TokenResponse(BaseModel):
    """Response after successful authentication."""

    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    display_name: str
    profile_completed: bool
    is_admin: bool


class ProfileUpdateRequest(BaseModel):
    """Request to update user profile."""

    display_name: str = Field(..., min_length=1, max_length=255)
    sex: str = Field(..., max_length=20)
    age: int = Field(..., ge=13, le=120)


class UserProfile(BaseModel):
    """User profile info returned by /auth/me and /auth/profile."""

    user_id: str
    email: str
    display_name: str
    sex: str | None
    age: int | None
    profile_completed: bool
    is_admin: bool


# Backwards-compatible aliases
ProfileResponse = UserProfile
UserInfo = UserProfile
