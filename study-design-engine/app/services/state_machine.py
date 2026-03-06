from datetime import datetime, timezone


class StudyStateMachine:
    """Enforces the study lifecycle state transitions from the PRD."""

    TRANSITIONS: dict[str, list[str]] = {
        "init": ["step_1_draft"],
        "step_1_draft": ["step_1_review"],
        "step_1_review": ["step_1_draft", "step_1_locked"],
        "step_1_locked": ["step_2_draft"],
        "step_2_draft": ["step_2_review"],
        "step_2_review": ["step_2_draft", "step_2_locked"],
        "step_2_locked": ["step_3_draft"],
        "step_3_draft": ["step_3_review"],
        "step_3_review": ["step_3_draft", "step_3_locked"],
        "step_3_locked": ["step_4_draft"],
        "step_4_draft": ["step_4_review"],
        "step_4_review": ["step_4_draft", "step_4_locked"],
        "step_4_locked": ["complete"],
        "complete": [],
    }

    STEP_PREREQUISITES: dict[int, str | None] = {
        1: None,
        2: "step_1_locked",
        3: "step_2_locked",
        4: "step_3_locked",
    }

    @staticmethod
    def can_transition(current_status: str, target_status: str) -> bool:
        """Check if a transition from current_status to target_status is valid."""
        valid_targets = StudyStateMachine.TRANSITIONS.get(current_status, [])
        return target_status in valid_targets

    @staticmethod
    def transition(study: object, target_status: str) -> object:
        """Transition a study to target_status. Raises ValueError if invalid."""
        current = study.status
        if not StudyStateMachine.can_transition(current, target_status):
            raise ValueError(
                f"Invalid transition from '{current}' to '{target_status}'. "
                f"Valid targets: {StudyStateMachine.TRANSITIONS.get(current, [])}"
            )
        study.status = target_status
        return study

    @staticmethod
    def can_start_step(study: object, step_number: int) -> bool:
        """Check if the study can start the given step."""
        prerequisite = StudyStateMachine.STEP_PREREQUISITES.get(step_number)
        if prerequisite is None:
            return True
        return study.status == prerequisite

    @staticmethod
    def can_edit_step(study: object, step_number: int) -> bool:
        """Check if the step can be edited (not locked)."""
        return not StudyStateMachine.is_step_locked(study, step_number)

    @staticmethod
    def can_lock_step(study: object, step_number: int) -> bool:
        """Check if the step can be locked (must be in review status)."""
        return study.status == f"step_{step_number}_review"

    @staticmethod
    def lock_step(study: object, step_number: int, user_id: str) -> object:
        """Lock a step. Transitions study status to step_N_locked."""
        target = f"step_{step_number}_locked"
        if not StudyStateMachine.can_lock_step(study, step_number):
            raise ValueError(
                f"Cannot lock step {step_number}: study must be in step_{step_number}_review status, "
                f"currently in '{study.status}'"
            )
        study.status = target
        return study

    @staticmethod
    def get_current_step(study: object) -> int:
        """Extract the current step number from the study status string."""
        status = study.status
        if status == "init":
            return 0
        if status == "complete":
            return 5
        # Status format: step_N_xxx
        parts = status.split("_")
        if len(parts) >= 2 and parts[0] == "step":
            try:
                return int(parts[1])
            except ValueError:
                return 0
        return 0

    @staticmethod
    def is_step_locked(study: object, step_number: int) -> bool:
        """Check if a specific step has been locked."""
        locked_status = f"step_{step_number}_locked"
        current_step = StudyStateMachine.get_current_step(study)
        # A step is locked if the study has progressed past it
        if study.status == locked_status:
            return True
        if study.status == "complete" and step_number <= 4:
            return True
        # If current step is greater than this step, it's locked
        if current_step > step_number:
            return True
        return False
