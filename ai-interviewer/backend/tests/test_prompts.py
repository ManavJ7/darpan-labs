"""Tests for prompt templates."""

import pytest
from pathlib import Path


PROMPTS_PATH = Path(__file__).parent.parent / "prompts"

REQUIRED_PROMPTS = [
    "interviewer_question.txt",
    "module_completion.txt",
    "transcript_correction.txt",
    "answer_parser.txt",
    "answer_satisfaction.txt",
]


class TestPromptFilesExist:
    """Tests for prompt file existence."""

    def test_prompts_directory_exists(self):
        """Test that prompts directory exists."""
        assert PROMPTS_PATH.exists(), "Prompts directory should exist"
        assert PROMPTS_PATH.is_dir(), "Prompts path should be a directory"

    @pytest.mark.parametrize("prompt_file", REQUIRED_PROMPTS)
    def test_required_prompt_file_exists(self, prompt_file):
        """Test that each required prompt file exists."""
        file_path = PROMPTS_PATH / prompt_file
        assert file_path.exists(), f"Missing prompt file: {prompt_file}"

    def test_all_required_prompts_exist(self):
        """Test that all required prompt files exist."""
        existing_prompts = [f.name for f in PROMPTS_PATH.glob("*.txt")]
        for prompt in REQUIRED_PROMPTS:
            assert prompt in existing_prompts, f"Missing: {prompt}"


class TestPromptFileContents:
    """Tests for prompt file contents."""

    @pytest.mark.parametrize("prompt_file", REQUIRED_PROMPTS)
    def test_prompt_file_not_empty(self, prompt_file):
        """Test that each prompt file is not empty."""
        file_path = PROMPTS_PATH / prompt_file
        content = file_path.read_text()
        assert len(content.strip()) > 0, f"{prompt_file} should not be empty"

    @pytest.mark.parametrize("prompt_file", REQUIRED_PROMPTS)
    def test_prompt_file_is_utf8(self, prompt_file):
        """Test that each prompt file is valid UTF-8."""
        file_path = PROMPTS_PATH / prompt_file
        try:
            content = file_path.read_text(encoding="utf-8")
            assert content is not None
        except UnicodeDecodeError:
            pytest.fail(f"{prompt_file} is not valid UTF-8")


class TestInterviewerQuestionPrompt:
    """Tests for interviewer_question.txt prompt."""

    def test_has_system_section(self):
        """Test that prompt has SYSTEM section."""
        content = (PROMPTS_PATH / "interviewer_question.txt").read_text()
        assert "SYSTEM:" in content or "system" in content.lower()

    def test_has_required_placeholders(self):
        """Test that prompt has required placeholders."""
        content = (PROMPTS_PATH / "interviewer_question.txt").read_text()
        required_placeholders = [
            "{module_name}",
            "{module_goal}",
            "{signal_targets}",
            "{module_id}",
            "{recent_turns}",
        ]
        for placeholder in required_placeholders:
            assert placeholder in content, f"Missing placeholder: {placeholder}"

    def test_has_output_format(self):
        """Test that prompt specifies output format."""
        content = (PROMPTS_PATH / "interviewer_question.txt").read_text()
        assert "OUTPUT" in content or "JSON" in content

    def test_has_action_types(self):
        """Test that prompt defines action types."""
        content = (PROMPTS_PATH / "interviewer_question.txt").read_text()
        assert "ASK_QUESTION" in content or "ask_question" in content.lower()


class TestModuleCompletionPrompt:
    """Tests for module_completion.txt prompt."""

    def test_prompt_exists_and_readable(self):
        """Test that module completion prompt is readable."""
        file_path = PROMPTS_PATH / "module_completion.txt"
        content = file_path.read_text()
        assert len(content) > 100, "Module completion prompt should have substantial content"


class TestTranscriptCorrectionPrompt:
    """Tests for transcript_correction.txt prompt."""

    def test_prompt_exists_and_readable(self):
        """Test that transcript correction prompt is readable."""
        file_path = PROMPTS_PATH / "transcript_correction.txt"
        content = file_path.read_text()
        assert len(content) > 50, "Transcript correction prompt should have content"

    def test_mentions_transcript_or_asr(self):
        """Test that prompt mentions transcript or ASR concepts."""
        content = (PROMPTS_PATH / "transcript_correction.txt").read_text()
        content_lower = content.lower()
        assert "transcript" in content_lower or "asr" in content_lower or "speech" in content_lower


class TestAnswerParserPrompt:
    """Tests for answer_parser.txt prompt."""

    def test_prompt_exists_and_readable(self):
        """Test that answer parser prompt is readable."""
        file_path = PROMPTS_PATH / "answer_parser.txt"
        content = file_path.read_text()
        assert len(content) > 50, "Answer parser prompt should have content"

    def test_mentions_parsing_or_analysis(self):
        """Test that prompt mentions parsing or analysis."""
        content = (PROMPTS_PATH / "answer_parser.txt").read_text()
        content_lower = content.lower()
        assert any(word in content_lower for word in ["parse", "analyz", "extract", "answer"])


class TestPromptConsistency:
    """Tests for consistency across prompts."""

    def test_all_prompts_have_reasonable_length(self):
        """Test that all prompts have reasonable length (not truncated)."""
        for prompt_file in REQUIRED_PROMPTS:
            file_path = PROMPTS_PATH / prompt_file
            content = file_path.read_text()
            # Each prompt should have at least 50 characters
            assert len(content) >= 50, f"{prompt_file} seems too short"

    def test_no_prompts_have_common_errors(self):
        """Test that prompts don't have common template errors."""
        for prompt_file in REQUIRED_PROMPTS:
            file_path = PROMPTS_PATH / prompt_file
            content = file_path.read_text()
            # Check for unclosed brackets
            assert content.count("{") == content.count("}"), \
                f"{prompt_file} has mismatched curly braces"

    def test_prompts_use_consistent_placeholder_style(self):
        """Test that prompts use curly brace placeholders consistently."""
        placeholder_count = 0
        for prompt_file in REQUIRED_PROMPTS:
            file_path = PROMPTS_PATH / prompt_file
            content = file_path.read_text()
            if "{" in content:
                placeholder_count += 1
        # At least some prompts should use placeholders
        assert placeholder_count >= 2, "Expected more prompts to use placeholders"
