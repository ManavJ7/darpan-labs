import uuid
from typing import Optional

from app.schemas.common import BaseSchema


class GoogleAuthRequest(BaseSchema):
    token: str


class UserResponse(BaseSchema):
    id: uuid.UUID
    email: str
    name: Optional[str] = None
    picture_url: Optional[str] = None


class AuthResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
