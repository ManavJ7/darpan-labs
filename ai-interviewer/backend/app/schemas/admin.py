"""Admin dashboard Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class AdminModuleSummary(BaseModel):
    """Module summary for admin user listing."""

    module_id: str
    status: str


class AdminUserSummary(BaseModel):
    """User summary for admin dashboard."""

    user_id: str
    email: str
    display_name: str
    sex: str | None
    age: int | None
    created_at: datetime
    modules: list[AdminModuleSummary]
    completed_module_count: int
    total_turns: int
    twin_status: str | None = None  # null, "building", "ready"


class AdminUserListResponse(BaseModel):
    """Paginated list of users for admin."""

    users: list[AdminUserSummary]
    total_count: int
    skip: int
    limit: int


class CreateTwinRequest(BaseModel):
    """Request to create a digital twin for a user."""

    n_twins: int = 1  # 1 = 1:1 mode, >1 = branched


class CreateTwinResponse(BaseModel):
    """Response after triggering twin creation."""

    job_id: str
    participant_id: str
    status: str
    status_url: str


class TwinSummary(BaseModel):
    """Summary of a digital twin."""

    twin_id: str
    twin_external_id: str
    mode: str
    coherence_score: float | None
    status: str
    created_at: datetime


class TwinStatusResponse(BaseModel):
    """Twin creation status for a user."""

    participant_id: str | None
    external_id: str | None
    twins: list[TwinSummary]
    latest_job: dict | None  # job status info


class JobStatusResponse(BaseModel):
    """Pipeline job status."""

    job_id: str
    job_type: str
    status: str
    current_step: str | None
    progress: dict | None
    result_summary: dict | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class TranscriptTurn(BaseModel):
    """Single Q&A turn in a transcript."""

    turn_index: int
    role: str
    question_text: str | None
    answer_text: str | None
    module_id: str
    created_at: datetime


class TranscriptModule(BaseModel):
    """Module section in a transcript."""

    module_id: str
    module_name: str
    status: str
    turns: list[TranscriptTurn]


class TranscriptResponse(BaseModel):
    """Full transcript for a user."""

    user_id: str
    display_name: str
    email: str
    sex: str | None
    age: int | None
    modules: list[TranscriptModule]
    total_turns: int
