"""
Shared data-loading and formatting utilities for the twin-generator pipeline.

Consolidates functions that were duplicated across step1, step2, step3,
backfill_questions, and explore_dimensions.
"""
from pathlib import Path

from config.settings import PROMPTS_DIR


def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = PROMPTS_DIR / filename
    with open(path) as f:
        return f.read()


def format_qa(qa_pairs: list[dict]) -> str:
    """Format Q&A pairs as a numbered text block for LLM prompts."""
    lines = []
    for i, qa in enumerate(qa_pairs, 1):
        lines.append(f"Q{i}: {qa['question_text']}")
        lines.append(f"A{i}: {qa['answer_text']}")
        lines.append("")
    return "\n".join(lines)


def format_questions_block(questions: list[dict]) -> str:
    """Format a batch of questions as a numbered list for LLM prompts."""
    lines = []
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. [{q['question_id']}] {q['question_text']}")
    return "\n".join(lines)


def count_dimension_diffs(choices_a: dict, choices_b: dict) -> int:
    """Count how many dimensions differ between two twin choice sets."""
    return sum(1 for k in choices_a if choices_a.get(k) != choices_b.get(k))
