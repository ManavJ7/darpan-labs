"""Study export service — assembles a full study payload for export."""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study import Study, StepVersion
from app.models.audit import ReviewComment, AuditLog
from app.schemas.study import StudyResponse, StepVersionResponse
from app.schemas.audit import AuditLogEntry, ReviewCommentResponse


class StudyExportService:
    """Assembles the complete study design into a single exportable dict."""

    @staticmethod
    async def export_study(
        study_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict:
        """Export the full study design as a nested dict.

        Includes study metadata, all step versions (latest per step),
        comments, and audit log.

        Args:
            study_id: The study to export.
            db: Async database session.

        Raises:
            HTTPException 404 if the study does not exist.

        Returns:
            A dict containing the assembled study export.
        """
        # Load study
        result = await db.execute(select(Study).where(Study.id == study_id))
        study = result.scalar_one_or_none()
        if study is None:
            raise HTTPException(status_code=404, detail="Study not found")

        study_response = StudyResponse(
            id=study.id,
            status=study.status,
            question=study.question,
            title=study.title,
            brand_name=study.brand_name,
            category=study.category,
            context=study.context,
            study_metadata=study.study_metadata,
            created_at=study.created_at,
            updated_at=study.updated_at,
        )

        # Load all step versions grouped by step, keeping only latest version per step
        versions_result = await db.execute(
            select(StepVersion)
            .where(StepVersion.study_id == study_id)
            .order_by(StepVersion.step.asc(), StepVersion.version.desc())
        )
        all_versions = versions_result.scalars().all()

        # Group by step — keep the latest version (first in desc order)
        steps: dict[int, dict] = {}
        all_versions_list: list[dict] = []
        for sv in all_versions:
            sv_resp = StepVersionResponse.model_validate(sv)
            all_versions_list.append(sv_resp.model_dump(mode="json"))
            if sv.step not in steps:
                steps[sv.step] = sv_resp.model_dump(mode="json")

        # Load comments
        comments_result = await db.execute(
            select(ReviewComment)
            .where(ReviewComment.study_id == study_id)
            .order_by(ReviewComment.created_at.desc())
        )
        comments = [
            ReviewCommentResponse.model_validate(c).model_dump(mode="json")
            for c in comments_result.scalars().all()
        ]

        # Load audit log
        audit_result = await db.execute(
            select(AuditLog)
            .where(AuditLog.study_id == study_id)
            .order_by(AuditLog.created_at.desc())
        )
        audit_log = [
            AuditLogEntry.model_validate(a).model_dump(mode="json")
            for a in audit_result.scalars().all()
        ]

        return {
            "study": study_response.model_dump(mode="json"),
            "steps": steps,
            "all_versions": all_versions_list,
            "comments": comments,
            "audit_log": audit_log,
        }
