"""Tests for SQLAlchemy database models."""

import uuid

from app.models.user import User
from app.models.consent import ConsentEvent
from app.models.interview import InterviewSession, InterviewModule, InterviewTurn


class TestUserModel:
    """Tests for User model."""

    def test_user_creation_with_required_fields(self):
        """Test User model instantiation with required fields."""
        user = User(
            email="test@example.com",
            display_name="Test User",
        )
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.auth_provider_id is None

    def test_user_creation_with_all_fields(self):
        """Test User model instantiation with all fields."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            display_name="Test User",
            auth_provider_id="google-oauth2|12345",
        )
        assert user.id == user_id
        assert user.auth_provider_id == "google-oauth2|12345"

    def test_user_repr(self):
        """Test User model string representation."""
        user = User(
            email="test@example.com",
            display_name="Test User",
        )
        assert "User" in repr(user)
        assert "test@example.com" in repr(user)


class TestConsentEventModel:
    """Tests for ConsentEvent model."""

    def test_consent_event_creation(self):
        """Test ConsentEvent model instantiation."""
        user_id = uuid.uuid4()
        consent = ConsentEvent(
            user_id=user_id,
            consent_type="interview",
            consent_version="1.0",
            accepted=True,
        )
        assert consent.user_id == user_id
        assert consent.consent_type == "interview"
        assert consent.consent_version == "1.0"
        assert consent.accepted is True
        assert consent.consent_metadata is None

    def test_consent_event_with_metadata(self):
        """Test ConsentEvent with metadata."""
        consent = ConsentEvent(
            user_id=uuid.uuid4(),
            consent_type="audio_storage",
            consent_version="1.0",
            accepted=True,
            consent_metadata={"ip_address": "127.0.0.1", "user_agent": "test"},
        )
        assert consent.consent_metadata["ip_address"] == "127.0.0.1"

    def test_consent_event_repr(self):
        """Test ConsentEvent string representation."""
        consent = ConsentEvent(
            user_id=uuid.uuid4(),
            consent_type="interview",
            consent_version="1.0",
            accepted=False,
        )
        assert "ConsentEvent" in repr(consent)
        assert "interview" in repr(consent)


class TestInterviewSessionModel:
    """Tests for InterviewSession model."""

    def test_interview_session_creation_defaults(self):
        """Test InterviewSession with default values.

        Note: SQLAlchemy column defaults are applied at DB level, not on object creation.
        We test that values can be set and optional fields are None when not provided.
        """
        user_id = uuid.uuid4()
        session = InterviewSession(
            user_id=user_id,
            status="active",
            input_mode="text",
            language_preference="auto",
        )
        assert session.user_id == user_id
        assert session.status == "active"
        assert session.input_mode == "text"
        assert session.language_preference == "auto"
        assert session.ended_at is None
        assert session.total_duration_sec is None

    def test_interview_session_creation_voice_mode(self):
        """Test InterviewSession with voice mode."""
        session = InterviewSession(
            user_id=uuid.uuid4(),
            status="active",
            input_mode="voice",
            language_preference="hi",
            settings={"sensitivity_settings": {"finance": False}},
        )
        assert session.input_mode == "voice"
        assert session.language_preference == "hi"
        assert session.settings["sensitivity_settings"]["finance"] is False

    def test_interview_session_repr(self):
        """Test InterviewSession string representation."""
        session = InterviewSession(user_id=uuid.uuid4(), status="completed")
        assert "InterviewSession" in repr(session)
        assert "completed" in repr(session)


class TestInterviewModuleModel:
    """Tests for InterviewModule model."""

    def test_interview_module_creation_defaults(self):
        """Test InterviewModule with default values.

        Note: SQLAlchemy column defaults are applied at DB level, not on object creation.
        """
        session_id = uuid.uuid4()
        module = InterviewModule(
            session_id=session_id,
            module_id="M1",
            status="pending",
            question_count=0,
            coverage_score=0.0,
            confidence_score=0.0,
        )
        assert module.session_id == session_id
        assert module.module_id == "M1"
        assert module.status == "pending"
        assert module.question_count == 0
        assert module.coverage_score == 0.0
        assert module.confidence_score == 0.0

    def test_interview_module_all_statuses(self):
        """Test InterviewModule with different statuses."""
        for status in ["pending", "active", "completed", "skipped"]:
            module = InterviewModule(
                session_id=uuid.uuid4(),
                module_id="M2",
                status=status,
            )
            assert module.status == status

    def test_interview_module_with_scores(self):
        """Test InterviewModule with coverage and confidence scores."""
        module = InterviewModule(
            session_id=uuid.uuid4(),
            module_id="M3",
            status="completed",
            question_count=10,
            coverage_score=0.85,
            confidence_score=0.9,
            signals_captured=["signal_1", "signal_2"],
            completion_eval={"passed": True, "reason": "All criteria met"},
        )
        assert module.question_count == 10
        assert module.coverage_score == 0.85
        assert module.confidence_score == 0.9
        assert "signal_1" in module.signals_captured

    def test_interview_module_repr(self):
        """Test InterviewModule string representation."""
        module = InterviewModule(
            session_id=uuid.uuid4(),
            module_id="M1",
            status="active",
        )
        assert "InterviewModule" in repr(module)
        assert "M1" in repr(module)


class TestInterviewTurnModel:
    """Tests for InterviewTurn model."""

    def test_interview_turn_interviewer(self):
        """Test InterviewTurn for interviewer role."""
        turn = InterviewTurn(
            session_id=uuid.uuid4(),
            module_id="M1",
            turn_index=0,
            role="interviewer",
            question_text="What is your occupation?",
            question_meta={"category": "identity", "type": "open_text"},
        )
        assert turn.role == "interviewer"
        assert turn.question_text == "What is your occupation?"
        assert turn.question_meta["category"] == "identity"

    def test_interview_turn_user_text(self):
        """Test InterviewTurn for user text response."""
        turn = InterviewTurn(
            session_id=uuid.uuid4(),
            module_id="M1",
            turn_index=1,
            role="user",
            input_mode="text",
            answer_text="I am a software engineer",
            answer_language="EN",
            answer_structured={"occupation": "software engineer"},
            answer_meta={"sentiment": "neutral", "specificity": "high"},
        )
        assert turn.role == "user"
        assert turn.answer_text == "I am a software engineer"
        assert turn.answer_language == "EN"

    def test_interview_turn_user_voice(self):
        """Test InterviewTurn for user voice response."""
        turn = InterviewTurn(
            session_id=uuid.uuid4(),
            module_id="M2",
            turn_index=3,
            role="user",
            input_mode="voice",
            answer_text="Main ek doctor hoon",
            answer_raw_transcript="main ek doctor hun",
            answer_language="HG",
            audio_meta={"duration_ms": 2500, "sample_rate": 16000, "asr_confidence": 0.95},
            audio_storage_ref="s3://bucket/audio/turn_123.wav",
        )
        assert turn.input_mode == "voice"
        assert turn.answer_raw_transcript == "main ek doctor hun"
        assert turn.audio_meta["asr_confidence"] == 0.95

    def test_interview_turn_repr(self):
        """Test InterviewTurn string representation."""
        turn = InterviewTurn(
            session_id=uuid.uuid4(),
            module_id="M1",
            turn_index=0,
            role="interviewer",
        )
        assert "InterviewTurn" in repr(turn)
        assert "interviewer" in repr(turn)


class TestModelTableNames:
    """Tests to verify correct table names for all models."""

    def test_all_table_names(self):
        """Verify all table names are correctly defined."""
        assert User.__tablename__ == "users"
        assert ConsentEvent.__tablename__ == "consent_events"
        assert InterviewSession.__tablename__ == "interview_sessions"
        assert InterviewModule.__tablename__ == "interview_modules"
        assert InterviewTurn.__tablename__ == "interview_turns"
