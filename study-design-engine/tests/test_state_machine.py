"""Tests for StudyStateMachine — 30+ tests."""
from unittest.mock import MagicMock

import pytest

from app.services.state_machine import StudyStateMachine


def make_study(status: str) -> MagicMock:
    study = MagicMock()
    study.status = status
    return study


class TestCanTransition:
    def test_init_to_step_1_draft(self):
        assert StudyStateMachine.can_transition("init", "step_1_draft") is True

    def test_init_to_step_2_draft_invalid(self):
        assert StudyStateMachine.can_transition("init", "step_2_draft") is False

    def test_init_to_complete_invalid(self):
        assert StudyStateMachine.can_transition("init", "complete") is False

    def test_step_1_draft_to_step_1_review(self):
        assert StudyStateMachine.can_transition("step_1_draft", "step_1_review") is True

    def test_step_1_review_to_step_1_locked(self):
        assert StudyStateMachine.can_transition("step_1_review", "step_1_locked") is True

    def test_step_1_review_to_step_1_draft(self):
        assert StudyStateMachine.can_transition("step_1_review", "step_1_draft") is True

    def test_step_1_locked_to_step_2_draft(self):
        assert StudyStateMachine.can_transition("step_1_locked", "step_2_draft") is True

    def test_step_1_locked_to_step_1_draft_invalid(self):
        assert StudyStateMachine.can_transition("step_1_locked", "step_1_draft") is False

    def test_step_2_review_to_step_2_locked(self):
        assert StudyStateMachine.can_transition("step_2_review", "step_2_locked") is True

    def test_step_3_review_to_step_3_locked(self):
        assert StudyStateMachine.can_transition("step_3_review", "step_3_locked") is True

    def test_step_4_review_to_step_4_locked(self):
        assert StudyStateMachine.can_transition("step_4_review", "step_4_locked") is True

    def test_step_4_locked_to_complete(self):
        assert StudyStateMachine.can_transition("step_4_locked", "complete") is True

    def test_complete_has_no_transitions(self):
        assert StudyStateMachine.can_transition("complete", "init") is False
        assert StudyStateMachine.can_transition("complete", "step_1_draft") is False

    def test_unknown_status_returns_false(self):
        assert StudyStateMachine.can_transition("unknown", "init") is False


class TestTransition:
    def test_valid_transition_updates_status(self):
        study = make_study("init")
        result = StudyStateMachine.transition(study, "step_1_draft")
        assert result.status == "step_1_draft"

    def test_invalid_transition_raises_value_error(self):
        study = make_study("init")
        with pytest.raises(ValueError, match="Invalid transition"):
            StudyStateMachine.transition(study, "step_2_draft")

    def test_transition_from_complete_raises(self):
        study = make_study("complete")
        with pytest.raises(ValueError):
            StudyStateMachine.transition(study, "init")


class TestCanStartStep:
    def test_can_start_step_1_from_init(self):
        study = make_study("init")
        # Step 1 has no prerequisite
        assert StudyStateMachine.can_start_step(study, 1) is True

    def test_can_start_step_2_requires_step_1_locked(self):
        study = make_study("step_1_locked")
        assert StudyStateMachine.can_start_step(study, 2) is True

    def test_cannot_start_step_2_from_init(self):
        study = make_study("init")
        assert StudyStateMachine.can_start_step(study, 2) is False

    def test_can_start_step_3_requires_step_2_locked(self):
        study = make_study("step_2_locked")
        assert StudyStateMachine.can_start_step(study, 3) is True

    def test_cannot_start_step_3_from_step_1_locked(self):
        study = make_study("step_1_locked")
        assert StudyStateMachine.can_start_step(study, 3) is False

    def test_can_start_step_4_requires_step_3_locked(self):
        study = make_study("step_3_locked")
        assert StudyStateMachine.can_start_step(study, 4) is True


class TestCanEditStep:
    def test_can_edit_step_1_when_in_draft(self):
        study = make_study("step_1_draft")
        assert StudyStateMachine.can_edit_step(study, 1) is True

    def test_cannot_edit_step_1_when_locked(self):
        study = make_study("step_1_locked")
        assert StudyStateMachine.can_edit_step(study, 1) is False

    def test_cannot_edit_step_1_when_complete(self):
        study = make_study("complete")
        assert StudyStateMachine.can_edit_step(study, 1) is False


class TestCanLockStep:
    def test_can_lock_step_1_in_review(self):
        study = make_study("step_1_review")
        assert StudyStateMachine.can_lock_step(study, 1) is True

    def test_cannot_lock_step_1_in_draft(self):
        study = make_study("step_1_draft")
        assert StudyStateMachine.can_lock_step(study, 1) is False


class TestLockStep:
    def test_lock_step_transitions_status(self):
        study = make_study("step_1_review")
        result = StudyStateMachine.lock_step(study, 1, "user_123")
        assert result.status == "step_1_locked"

    def test_lock_step_raises_if_not_in_review(self):
        study = make_study("step_1_draft")
        with pytest.raises(ValueError, match="Cannot lock step"):
            StudyStateMachine.lock_step(study, 1, "user_123")


class TestGetCurrentStep:
    def test_init_returns_0(self):
        study = make_study("init")
        assert StudyStateMachine.get_current_step(study) == 0

    def test_step_1_draft_returns_1(self):
        study = make_study("step_1_draft")
        assert StudyStateMachine.get_current_step(study) == 1

    def test_step_3_review_returns_3(self):
        study = make_study("step_3_review")
        assert StudyStateMachine.get_current_step(study) == 3

    def test_complete_returns_5(self):
        study = make_study("complete")
        assert StudyStateMachine.get_current_step(study) == 5


class TestIsStepLocked:
    def test_step_1_locked_when_status_is_step_1_locked(self):
        study = make_study("step_1_locked")
        assert StudyStateMachine.is_step_locked(study, 1) is True

    def test_step_1_not_locked_when_in_draft(self):
        study = make_study("step_1_draft")
        assert StudyStateMachine.is_step_locked(study, 1) is False

    def test_step_1_locked_when_on_step_3(self):
        study = make_study("step_3_draft")
        assert StudyStateMachine.is_step_locked(study, 1) is True

    def test_all_steps_locked_when_complete(self):
        study = make_study("complete")
        for step in range(1, 5):
            assert StudyStateMachine.is_step_locked(study, step) is True
