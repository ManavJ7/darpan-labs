"""Router for Metric Library CRUD endpoints."""

from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.metric import MetricCreate, MetricResponse
from app.services.metric_library_service import MetricLibraryService

router = APIRouter(prefix="/api/v1/metrics", tags=["Metrics"])


@router.get("/", response_model=list[MetricResponse], summary="List metrics")
async def list_metrics(
    study_type: Optional[str] = Query(None, description="Filter by applicable study type"),
    db: AsyncSession = Depends(get_session),
):
    """Return all metrics, optionally filtered by study_type applicability."""
    return await MetricLibraryService.list_metrics(study_type, db)


@router.get("/{metric_id}", response_model=MetricResponse, summary="Get metric")
async def get_metric(
    metric_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Return a single metric by ID."""
    return await MetricLibraryService.get_metric(metric_id, db)


@router.post("/", response_model=MetricResponse, status_code=201, summary="Create metric")
async def create_metric(
    data: MetricCreate,
    db: AsyncSession = Depends(get_session),
):
    """Create a new metric in the library."""
    return await MetricLibraryService.create_metric(data, db)


@router.patch("/{metric_id}", response_model=MetricResponse, summary="Update metric")
async def update_metric(
    metric_id: str,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_session),
):
    """Partially update an existing metric."""
    return await MetricLibraryService.update_metric(metric_id, data, db)


@router.delete("/{metric_id}", status_code=204, summary="Delete metric")
async def delete_metric(
    metric_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Delete a metric from the library."""
    await MetricLibraryService.delete_metric(metric_id, db)


@router.post("/seed", summary="Seed metrics from file")
async def seed_metrics(
    db: AsyncSession = Depends(get_session),
):
    """Load metrics from seed_data/metric_library.json and upsert all."""
    count = await MetricLibraryService.seed_metrics(db)
    return {"seeded": count}
