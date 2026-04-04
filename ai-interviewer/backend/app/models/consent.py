"""Consent event model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConsentEvent(Base):
    """Consent event tracking model."""

    __tablename__ = "consent_events"

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
    consent_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # "interview", "audio_storage", "sensitive_topics", "data_retention"
    consent_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    accepted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    consent_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="consent_events",
    )

    def __repr__(self) -> str:
        return f"<ConsentEvent(id={self.id}, type={self.consent_type}, accepted={self.accepted})>"
