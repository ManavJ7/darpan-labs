"""Router for Review Comment endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.audit import ReviewCommentCreate, ReviewCommentResponse
from app.services.review_comment_service import ReviewCommentService

router = APIRouter(prefix="/api/v1/studies/{study_id}/comments", tags=["Comments"])


@router.post("/", response_model=ReviewCommentResponse, status_code=201, summary="Add comment")
async def add_comment(
    study_id: uuid.UUID,
    data: ReviewCommentCreate,
    db: AsyncSession = Depends(get_session),
):
    """Add a review comment to a study step."""
    return await ReviewCommentService.add_comment(study_id, data, db)


@router.get("/", response_model=list[ReviewCommentResponse], summary="List comments")
async def list_comments(
    study_id: uuid.UUID,
    step: Optional[int] = Query(None, description="Filter by step number"),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    db: AsyncSession = Depends(get_session),
):
    """Return comments for a study with optional filters."""
    return await ReviewCommentService.list_comments(study_id, step, resolved, db)


@router.post(
    "/{comment_id}/resolve",
    response_model=ReviewCommentResponse,
    summary="Resolve comment",
)
async def resolve_comment(
    study_id: uuid.UUID,
    comment_id: uuid.UUID,
    resolved_by: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_session),
):
    """Mark a review comment as resolved."""
    return await ReviewCommentService.resolve_comment(comment_id, resolved_by, db)
