"""Metric library CRUD service — manages the standard research metric catalogue."""

import json
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric import MetricLibrary
from app.schemas.metric import MetricCreate, MetricResponse


class MetricLibraryService:
    """CRUD operations for the metric_library table."""

    SEED_FILE = Path(__file__).parent.parent.parent / "seed_data" / "metric_library.json"

    @staticmethod
    async def list_metrics(
        study_type: Optional[str],
        db: AsyncSession,
    ) -> list[MetricResponse]:
        """List metrics, optionally filtered by study_type applicability.

        Args:
            study_type: If provided, only return metrics whose
                        applicable_study_types array contains this value.
            db: Async database session.

        Returns:
            List of MetricResponse schemas.
        """
        query = select(MetricLibrary)
        if study_type is not None:
            query = query.where(
                MetricLibrary.applicable_study_types.any(study_type)
            )
        result = await db.execute(query)
        metrics = result.scalars().all()
        return [MetricResponse.model_validate(m) for m in metrics]

    @staticmethod
    async def get_metric(
        metric_id: str,
        db: AsyncSession,
    ) -> MetricResponse:
        """Get a single metric by its ID.

        Raises:
            HTTPException 404 if the metric does not exist.
        """
        result = await db.execute(
            select(MetricLibrary).where(MetricLibrary.id == metric_id)
        )
        metric = result.scalar_one_or_none()
        if metric is None:
            raise HTTPException(status_code=404, detail=f"Metric '{metric_id}' not found")
        return MetricResponse.model_validate(metric)

    @staticmethod
    async def create_metric(
        data: MetricCreate,
        db: AsyncSession,
    ) -> MetricResponse:
        """Create a new metric in the library.

        Raises:
            HTTPException 409 if a metric with the same ID already exists.
        """
        existing = await db.execute(
            select(MetricLibrary).where(MetricLibrary.id == data.id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Metric '{data.id}' already exists",
            )
        metric = MetricLibrary(
            id=data.id,
            display_name=data.display_name,
            category=data.category,
            description=data.description,
            applicable_study_types=data.applicable_study_types,
            default_scale=data.default_scale,
            benchmark_available=data.benchmark_available,
        )
        db.add(metric)
        await db.commit()
        await db.refresh(metric)
        return MetricResponse.model_validate(metric)

    @staticmethod
    async def update_metric(
        metric_id: str,
        data: dict,
        db: AsyncSession,
    ) -> MetricResponse:
        """Partial update a metric by ID.

        Args:
            metric_id: The metric to update.
            data: Dict of fields to update.
            db: Async database session.

        Raises:
            HTTPException 404 if not found.

        Returns:
            Updated MetricResponse.
        """
        result = await db.execute(
            select(MetricLibrary).where(MetricLibrary.id == metric_id)
        )
        metric = result.scalar_one_or_none()
        if metric is None:
            raise HTTPException(status_code=404, detail=f"Metric '{metric_id}' not found")

        allowed_fields = {
            "display_name", "category", "description",
            "applicable_study_types", "default_scale", "benchmark_available",
        }
        for key, value in data.items():
            if key in allowed_fields:
                setattr(metric, key, value)

        await db.commit()
        await db.refresh(metric)
        return MetricResponse.model_validate(metric)

    @staticmethod
    async def delete_metric(
        metric_id: str,
        db: AsyncSession,
    ) -> None:
        """Delete a metric by ID.

        Raises:
            HTTPException 404 if not found.
        """
        result = await db.execute(
            select(MetricLibrary).where(MetricLibrary.id == metric_id)
        )
        metric = result.scalar_one_or_none()
        if metric is None:
            raise HTTPException(status_code=404, detail=f"Metric '{metric_id}' not found")
        await db.delete(metric)
        await db.commit()

    @staticmethod
    async def seed_metrics(db: AsyncSession) -> int:
        """Load metrics from the seed_data/metric_library.json file and upsert all.

        Returns:
            Number of metrics upserted.
        """
        if not MetricLibraryService.SEED_FILE.exists():
            raise HTTPException(
                status_code=500,
                detail="Seed file not found at expected path",
            )

        raw = MetricLibraryService.SEED_FILE.read_text(encoding="utf-8")
        metrics_data: list[dict] = json.loads(raw)

        count = 0
        for item in metrics_data:
            result = await db.execute(
                select(MetricLibrary).where(MetricLibrary.id == item["id"])
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                # Update existing
                for key, value in item.items():
                    if key != "id":
                        setattr(existing, key, value)
            else:
                # Insert new
                metric = MetricLibrary(**item)
                db.add(metric)
            count += 1

        await db.commit()
        return count
