"""Mirror models for shared twin pipeline tables.

These map to the same DB tables created by the AI Interviewer migration.
The SDE reads/writes these tables for simulation management.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Participant(Base):
    """Research participant (read-only from SDE perspective)."""

    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    twins: Mapped[list["DigitalTwin"]] = relationship("DigitalTwin", back_populates="participant")


class DigitalTwin(Base):
    """Digital twin (read for listing, referenced by simulation)."""

    __tablename__ = "digital_twins"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False, index=True,
    )
    twin_external_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    coherence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="building")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    participant: Mapped["Participant"] = relationship("Participant", back_populates="twins")
    simulation_runs: Mapped[list["TwinSimulationRun"]] = relationship(
        "TwinSimulationRun", back_populates="twin",
    )


class PipelineJob(Base):
    """Pipeline job tracking (created by SDE for simulation jobs)."""

    __tablename__ = "pipeline_jobs"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(30), nullable=False)
    participant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        pg.UUID(as_uuid=True), nullable=True,
    )
    study_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    current_step: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    progress: Mapped[Optional[dict]] = mapped_column(pg.JSONB, nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(pg.JSONB, nullable=True)
    result_summary: Mapped[Optional[dict]] = mapped_column(pg.JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ValidationReport(Base):
    """Validation report comparing twin simulation results (optionally vs real responses)."""

    __tablename__ = "validation_reports"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("studies.id"), nullable=False, index=True)
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("pipeline_jobs.id", ondelete="SET NULL"), nullable=True,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # comparison, synthesis
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    twin_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    real_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    report_data: Mapped[Optional[dict]] = mapped_column(pg.JSONB, nullable=True)  # full validation output
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class TwinSimulationRun(Base):
    """Unified simulation run (replaces old SDE SimulationRun for twin simulations)."""

    __tablename__ = "simulation_runs"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("pipeline_jobs.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    twin_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("digital_twins.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    study_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True, index=True)
    questionnaire_snapshot: Mapped[dict] = mapped_column(pg.JSONB, nullable=False)
    inference_mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default="combined")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    responses: Mapped[Optional[list]] = mapped_column(pg.JSONB, nullable=True)
    summary_stats: Mapped[Optional[dict]] = mapped_column(pg.JSONB, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    twin: Mapped["DigitalTwin"] = relationship("DigitalTwin", back_populates="simulation_runs")
