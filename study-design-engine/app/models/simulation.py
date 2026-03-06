import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("studies.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    inference_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    twin_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    question_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    results: Mapped[dict] = mapped_column(pg.JSONB, nullable=False)
    summary: Mapped[Optional[dict]] = mapped_column(pg.JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
