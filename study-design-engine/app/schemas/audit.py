import uuid
from datetime import datetime
from typing import Optional

from app.schemas.common import BaseSchema


class AuditLogEntry(BaseSchema):
    id: uuid.UUID
    study_id: uuid.UUID
    action: str
    actor: str
    payload: Optional[dict] = None
    created_at: datetime


class ReviewCommentCreate(BaseSchema):
    step: int
    target_type: str  # step | concept | question | section
    target_id: Optional[str] = None
    comment_text: str


class ReviewCommentResponse(BaseSchema):
    id: uuid.UUID
    study_id: uuid.UUID
    step: int
    target_type: str
    target_id: Optional[str] = None
    comment_text: str
    resolved: bool
    resolved_by: Optional[str] = None
    created_at: datetime
