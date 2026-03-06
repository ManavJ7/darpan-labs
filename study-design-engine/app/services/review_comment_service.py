"""Review comment service — manages inline review comments on study steps."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import ReviewComment
from app.models.study import Study
from app.schemas.audit import ReviewCommentCreate, ReviewCommentResponse


class ReviewCommentService:
    """CRUD for review comments attached to study steps."""

    @staticmethod
    async def add_comment(
        study_id: uuid.UUID,
        data: ReviewCommentCreate,
        db: AsyncSession,
    ) -> ReviewCommentResponse:
        """Add a review comment to a study step.

        Args:
            study_id: The study the comment belongs to.
            data: Comment creation payload.
            db: Async database session.

        Raises:
            HTTPException 404 if the study does not exist.

        Returns:
            ReviewCommentResponse for the created comment.
        """
        # Verify study exists
        result = await db.execute(select(Study).where(Study.id == study_id))
        study = result.scalar_one_or_none()
        if study is None:
            raise HTTPException(status_code=404, detail="Study not found")

        now = datetime.now(timezone.utc)
        comment = ReviewComment(
            id=uuid.uuid4(),
            study_id=study_id,
            step=data.step,
            target_type=data.target_type,
            target_id=data.target_id,
            comment_text=data.comment_text,
            resolved=False,
            created_at=now,
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return ReviewCommentResponse.model_validate(comment)

    @staticmethod
    async def list_comments(
        study_id: uuid.UUID,
        step: Optional[int],
        resolved: Optional[bool],
        db: AsyncSession,
    ) -> list[ReviewCommentResponse]:
        """List comments for a study with optional filters.

        Args:
            study_id: The study to query.
            step: If provided, filter to this step number.
            resolved: If provided, filter by resolved flag.
            db: Async database session.

        Returns:
            List of ReviewCommentResponse ordered by creation time descending.
        """
        query = (
            select(ReviewComment)
            .where(ReviewComment.study_id == study_id)
            .order_by(ReviewComment.created_at.desc())
        )
        if step is not None:
            query = query.where(ReviewComment.step == step)
        if resolved is not None:
            query = query.where(ReviewComment.resolved == resolved)

        result = await db.execute(query)
        comments = result.scalars().all()
        return [ReviewCommentResponse.model_validate(c) for c in comments]

    @staticmethod
    async def resolve_comment(
        comment_id: uuid.UUID,
        resolved_by: str,
        db: AsyncSession,
    ) -> ReviewCommentResponse:
        """Mark a review comment as resolved.

        Args:
            comment_id: The comment to resolve.
            resolved_by: User who resolved the comment.
            db: Async database session.

        Raises:
            HTTPException 404 if the comment does not exist.
            HTTPException 409 if the comment is already resolved.

        Returns:
            Updated ReviewCommentResponse.
        """
        result = await db.execute(
            select(ReviewComment).where(ReviewComment.id == comment_id)
        )
        comment = result.scalar_one_or_none()
        if comment is None:
            raise HTTPException(status_code=404, detail="Comment not found")
        if comment.resolved:
            raise HTTPException(status_code=409, detail="Comment already resolved")

        comment.resolved = True
        comment.resolved_by = resolved_by

        await db.commit()
        await db.refresh(comment)
        return ReviewCommentResponse.model_validate(comment)
