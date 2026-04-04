"""Interview models: Session, Module, Turn."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InterviewSession(Base):
    """Interview session model."""

    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )  # active, completed, paused
    input_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="text",
    )  # voice, text, mixed
    language_preference: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="auto",
    )  # auto, en, hi
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    total_duration_sec: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    settings: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # sensitivity_settings, topic preferences

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="interview_sessions",
    )
    modules: Mapped[list["InterviewModule"]] = relationship(
        "InterviewModule",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    turns: Mapped[list["InterviewTurn"]] = relationship(
        "InterviewTurn",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<InterviewSession(id={self.id}, status={self.status})>"


class InterviewModule(Base):
    """Interview module tracking model."""

    __tablename__ = "interview_modules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module_id: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )  # M1, M2, M3, M4, A1-A6
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )  # pending, active, completed, skipped
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    question_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    coverage_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    signals_captured: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # list of captured signal names
    completion_eval: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # LLM evaluation output

    # Relationships
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        back_populates="modules",
    )

    def __repr__(self) -> str:
        return f"<InterviewModule(id={self.id}, module_id={self.module_id}, status={self.status})>"


class InterviewTurn(Base):
    """Interview turn (question/answer) model."""

    __tablename__ = "interview_turns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module_id: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    turn_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # interviewer, user, system
    input_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="text",
    )  # voice, text

    # Question fields (for interviewer turns)
    question_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    question_meta: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # category, type, rationale, target_signal

    # Answer fields (for user turns)
    answer_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    answer_raw_transcript: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # raw ASR before correction
    answer_language: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )  # EN, HI, HG (Hinglish)
    answer_structured: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    answer_meta: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # sentiment, specificity, confidence

    # Audio metadata (for voice turns)
    audio_meta: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # duration_ms, sample_rate, vad_events, asr_confidence
    audio_storage_ref: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )  # S3 path, TTL

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        back_populates="turns",
    )

    def __repr__(self) -> str:
        return f"<InterviewTurn(id={self.id}, module={self.module_id}, role={self.role})>"
