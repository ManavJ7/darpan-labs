"""Version history service — browse step version snapshots for a study."""

import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study import StepVersion
from app.schemas.study import StepVersionResponse


class VersionHistoryService:
    """Read-only queries for step version history."""

    @staticmethod
    async def get_versions(
        study_id: uuid.UUID,
        step: Optional[int],
        db: AsyncSession,
    ) -> list[StepVersionResponse]:
        """List all versions for a study, optionally filtered by step.

        Args:
            study_id: The study to query.
            step: If provided, filter to this step number.
            db: Async database session.

        Returns:
            List of StepVersionResponse ordered by step then version ascending.
        """
        query = (
            select(StepVersion)
            .where(StepVersion.study_id == study_id)
            .order_by(StepVersion.step.asc(), StepVersion.version.asc())
        )
        if step is not None:
            query = query.where(StepVersion.step == step)

        result = await db.execute(query)
        versions = result.scalars().all()
        return [StepVersionResponse.model_validate(v) for v in versions]

    @staticmethod
    async def get_version(
        study_id: uuid.UUID,
        step: int,
        version: int,
        db: AsyncSession,
    ) -> StepVersionResponse:
        """Get a specific step version by study, step, and version number.

        Raises:
            HTTPException 404 if the version does not exist.
        """
        result = await db.execute(
            select(StepVersion).where(
                StepVersion.study_id == study_id,
                StepVersion.step == step,
                StepVersion.version == version,
            )
        )
        sv = result.scalar_one_or_none()
        if sv is None:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version} of step {step} not found for study {study_id}",
            )
        return StepVersionResponse.model_validate(sv)
