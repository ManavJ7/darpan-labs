"""Twin pipeline models: Participant, DigitalTwin, PipelineJob, PipelineStepOutput, SimulationRun."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Participant(Base):
    """Research participant whose interview data feeds the twin pipeline."""

    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    external_id: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )  # "P01", "P19", etc.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    profile_qa: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )  # [{question_text, answer_text, module_id}]
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="interview",
        server_default="interview",
    )  # interview, import
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
    )
    twins: Mapped[list["DigitalTwin"]] = relationship(
        "DigitalTwin",
        back_populates="participant",
        cascade="all, delete-orphan",
    )
    step_outputs: Mapped[list["PipelineStepOutput"]] = relationship(
        "PipelineStepOutput",
        back_populates="participant",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Participant(id={self.id}, external_id={self.external_id})>"


class DigitalTwin(Base):
    """A generated digital twin linked to a participant."""

    __tablename__ = "digital_twins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    twin_external_id: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )  # "P01_T001"
    mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # branched, 1to1
    combo_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    coherence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    branch_choices: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    profile_data: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )  # full ~350 QA pairs from step3
    profile_stats: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # {n_real, n_branch, n_synthetic, n_total}
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="building",
        server_default="building",
    )  # building, ready
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    participant: Mapped["Participant"] = relationship(
        "Participant",
        back_populates="twins",
    )
    simulation_runs: Mapped[list["SimulationRun"]] = relationship(
        "SimulationRun",
        back_populates="twin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DigitalTwin(id={self.id}, twin_external_id={self.twin_external_id}, status={self.status})>"


class PipelineJob(Base):
    """Tracks background job execution for twin creation or simulation."""

    __tablename__ = "pipeline_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )  # create_twin, run_simulation
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    study_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )  # FK to studies.id conceptually, no hard FK to avoid cross-service coupling
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )  # pending, running, completed, failed
    current_step: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )  # step2, step3, step4a, step4b, step5
    progress: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # {step2: "completed", step3: "running", ...}
    config: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # {n_twins, inference_mode, ...}
    result_summary: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<PipelineJob(id={self.id}, type={self.job_type}, status={self.status})>"


class PipelineStepOutput(Base):
    """Intermediate output of each pipeline step for a participant."""

    __tablename__ = "pipeline_step_outputs"
    __table_args__ = (
        UniqueConstraint("participant_id", "step_name", "mode", name="uq_step_output_per_participant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    step_name: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )  # step2_dimensions, step2_archetypes, step2_pruned, step3_profiles, step4_kg
    mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="1to1",
        server_default="1to1",
    )  # branched, 1to1
    output_data: Mapped[dict | list] = mapped_column(
        JSONB,
        nullable=False,
    )
    file_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )  # filesystem path for binary outputs (ChromaDB dir)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    participant: Mapped["Participant"] = relationship(
        "Participant",
        back_populates="step_outputs",
    )

    def __repr__(self) -> str:
        return f"<PipelineStepOutput(id={self.id}, step={self.step_name}, participant={self.participant_id})>"


class ValidationReport(Base):
    """Validation report comparing twin simulation results (optionally vs real responses)."""

    __tablename__ = "validation_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # comparison, synthesis
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending",
    )
    twin_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    real_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    def __repr__(self) -> str:
        return f"<ValidationReport(id={self.id}, mode={self.mode}, status={self.status})>"


class SimulationRun(Base):
    """Step 5 simulation execution and results."""

    __tablename__ = "simulation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    twin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("digital_twins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    study_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )  # links to SDE study
    questionnaire_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )  # snapshot of questions + concepts at simulation time
    inference_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="combined",
        server_default="combined",
    )  # vector, kg, combined
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )  # pending, running, completed, failed
    responses: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # list of response dicts
    summary_stats: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    twin: Mapped["DigitalTwin"] = relationship(
        "DigitalTwin",
        back_populates="simulation_runs",
    )

    def __repr__(self) -> str:
        return f"<SimulationRun(id={self.id}, twin={self.twin_id}, status={self.status})>"
