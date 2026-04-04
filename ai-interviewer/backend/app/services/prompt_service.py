"""Prompt template loading and formatting service."""

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Prompts directory relative to this file
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class PromptService:
    """Load and format prompt templates from files."""

    def __init__(self, prompts_dir: Path | None = None):
        """Initialize prompt service.

        Args:
            prompts_dir: Directory containing prompt files. Defaults to /prompts.
        """
        self.prompts_dir = prompts_dir or PROMPTS_DIR
        self._cache: dict[str, str] = {}

    def load_prompt(self, prompt_name: str) -> str:
        """Load prompt template from file.

        Args:
            prompt_name: Name of the prompt file (without .txt extension).

        Returns:
            The prompt template string.

        Raises:
            FileNotFoundError: If prompt file doesn't exist.
        """
        # Always reload from disk in development for hot-reloading prompts
        if prompt_name in self._cache:
            prompt_path = self.prompts_dir / f"{prompt_name}.txt"
            if prompt_path.exists():
                current = prompt_path.read_text(encoding="utf-8")
                if current != self._cache[prompt_name]:
                    self._cache[prompt_name] = current
                    logger.debug(f"Reloaded changed prompt: {prompt_name}")
            return self._cache[prompt_name]

        prompt_path = self.prompts_dir / f"{prompt_name}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        content = prompt_path.read_text(encoding="utf-8")
        self._cache[prompt_name] = content
        logger.debug(f"Loaded prompt: {prompt_name}")
        return content

    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """Load and format prompt with placeholders.

        Args:
            prompt_name: Name of the prompt file.
            **kwargs: Values to substitute for placeholders.

        Returns:
            Formatted prompt string.
        """
        template = self.load_prompt(prompt_name)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing placeholder in prompt {prompt_name}: {e}")
            raise ValueError(f"Missing required placeholder: {e}")

    def get_answer_parser_prompt(
        self,
        module_id: str,
        module_name: str,
        question_text: str,
        target_signal: str,
        answer_text: str,
        previous_answers: list[dict],
        signal_targets: list[str] | None = None,
    ) -> str:
        """Format the answer_parser.txt prompt.

        Args:
            module_id: Current module ID (e.g., "M1").
            module_name: Human-readable module name.
            question_text: The question that was asked.
            target_signal: The signal this question targets.
            answer_text: The user's answer.
            previous_answers: List of previous Q&A in this module.
            signal_targets: Valid signal names for this module.

        Returns:
            Formatted prompt ready for LLM.
        """
        previous_str = self._format_previous_answers(previous_answers)
        signals_str = json.dumps(signal_targets or [])
        return self.format_prompt(
            "answer_parser",
            module_id=module_id,
            module_name=module_name,
            question_text=question_text,
            target_signal=target_signal,
            answer_text=answer_text,
            previous_answers=previous_str,
            signal_targets=signals_str,
        )

    def get_module_completion_prompt(
        self,
        module_id: str,
        module_name: str,
        signal_targets: list[str],
        coverage_threshold: float,
        confidence_threshold: float,
        module_turns: list[dict],
    ) -> str:
        """Format the module_completion.txt prompt.

        Args:
            module_id: Current module ID.
            module_name: Human-readable module name.
            signal_targets: List of signals this module should capture.
            coverage_threshold: Required coverage score.
            confidence_threshold: Required confidence score.
            module_turns: All Q&A turns in this module.

        Returns:
            Formatted prompt ready for LLM.
        """
        turns_str = self._format_module_turns(module_turns)
        signals_str = json.dumps(signal_targets)
        return self.format_prompt(
            "module_completion",
            module_id=module_id,
            module_name=module_name,
            signal_targets=signals_str,
            coverage_threshold=coverage_threshold,
            confidence_threshold=confidence_threshold,
            module_turns=turns_str,
        )

    def get_interviewer_question_prompt(
        self,
        module_id: str,
        module_name: str,
        module_goal: str,
        signal_targets: list[str],
        questions_asked: int,
        max_questions: int,
        coverage: float,
        confidence: float,
        captured_signals: list[str],
        missing_signals: list[str],
        recent_turns: list[dict],
        cross_module_summary: str,
        sensitivity_settings: dict,
        conversation_state: dict | None = None,
    ) -> str:
        """Format the interviewer_question.txt prompt.

        Args:
            module_id: Current module ID.
            module_name: Human-readable module name.
            module_goal: Goal of this module.
            signal_targets: All target signals for this module.
            questions_asked: Number of questions asked so far.
            max_questions: Maximum questions for this module.
            coverage: Current coverage score.
            confidence: Current confidence score.
            captured_signals: Signals already captured.
            missing_signals: Signals still needed.
            recent_turns: Recent Q&A turns for context.
            cross_module_summary: Summary from completed modules.
            sensitivity_settings: User's sensitivity preferences.
            conversation_state: Cumulative session memory (open loops, style markers, etc.).

        Returns:
            Formatted prompt ready for LLM.
        """
        recent_turns_str = self._format_recent_turns(recent_turns)
        signals_str = json.dumps(signal_targets)
        captured_str = json.dumps(captured_signals)
        missing_str = json.dumps(missing_signals)
        sensitivity_str = json.dumps(sensitivity_settings)
        conversation_state_str = json.dumps(conversation_state or {}, indent=2)

        return self.format_prompt(
            "interviewer_question",
            module_id=module_id,
            module_name=module_name,
            module_goal=module_goal,
            signal_targets=signals_str,
            questions_asked=questions_asked,
            max_questions=max_questions,
            coverage=coverage,
            confidence=confidence,
            captured_signals=captured_str,
            missing_signals=missing_str,
            recent_turns=recent_turns_str,
            cross_module_summary=cross_module_summary,
            sensitivity_settings=sensitivity_str,
            conversation_state=conversation_state_str,
        )

    def get_followup_probe_prompt(
        self,
        question_text: str,
        target_signal: str,
        answer_text: str,
        followup_attempt: int,
        followup_reason: str,
        previous_context: str = "",
        module_goal: str = "",
    ) -> str:
        """Format the followup_probe.txt prompt.

        Args:
            question_text: The question that was asked.
            target_signal: The signal we're targeting.
            answer_text: The user's vague answer.
            followup_attempt: Which attempt this is (1 or 2).
            followup_reason: Why we're following up.
            previous_context: Brief context from earlier conversation.
            module_goal: Goal of the current module for context.

        Returns:
            Formatted prompt ready for LLM.
        """
        return self.format_prompt(
            "followup_probe",
            question_text=question_text,
            target_signal=target_signal,
            answer_text=answer_text,
            followup_attempt=followup_attempt,
            followup_reason=followup_reason,
            previous_context=previous_context,
            module_goal=module_goal,
        )

    def get_answer_satisfaction_prompt(
        self,
        question_text: str,
        answer_text: str,
        target_signal: str = "",
    ) -> str:
        """Format the answer_satisfaction.txt prompt."""
        return self.format_prompt(
            "answer_satisfaction",
            question_text=question_text,
            answer_text=answer_text,
            target_signal=target_signal,
        )

    def get_acknowledgment_prompt(
        self,
        answer_text: str,
        question_text: str,
    ) -> str:
        """Format the acknowledgment.txt prompt.

        Args:
            answer_text: The user's answer to acknowledge.
            question_text: The question that was asked.

        Returns:
            Formatted prompt ready for LLM.
        """
        return self.format_prompt(
            "acknowledgment",
            answer_text=answer_text,
            question_text=question_text,
        )

    def _format_previous_answers(self, previous_answers: list[dict]) -> str:
        """Format previous answers for prompt inclusion."""
        if not previous_answers:
            return "No previous answers in this module."

        lines = []
        for i, qa in enumerate(previous_answers, 1):
            q = qa.get("question", "")
            a = qa.get("answer", "")
            lines.append(f"{i}. Q: {q}\n   A: {a}")
        return "\n".join(lines)

    def _format_module_turns(self, turns: list[dict]) -> str:
        """Format module turns for completion evaluation."""
        if not turns:
            return "No turns recorded."

        lines = []
        for i, turn in enumerate(turns, 1):
            q = turn.get("question", "")
            a = turn.get("answer", "")
            signal = turn.get("target_signal", "")
            lines.append(f"Turn {i} [signal: {signal}]:\n  Q: {q}\n  A: {a}")
        return "\n\n".join(lines)

    def _format_recent_turns(self, turns: list[dict], max_turns: int = 5) -> str:
        """Format recent turns for context."""
        if not turns:
            return "No previous turns."

        recent = turns[-max_turns:] if len(turns) > max_turns else turns
        lines = []
        for turn in recent:
            role = turn.get("role", "")
            content = turn.get("question") or turn.get("answer", "")
            lines.append(f"[{role}]: {content}")
        return "\n".join(lines)

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self._cache.clear()


# Singleton instance
_prompt_service: PromptService | None = None


def get_prompt_service() -> PromptService:
    """Get the singleton prompt service instance."""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService()
    return _prompt_service
