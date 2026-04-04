"""Tests for seed data (question banks)."""

import json
import pytest
from pathlib import Path


SEED_DATA_PATH = Path(__file__).parent.parent / "seed_data" / "question_banks"

REQUIRED_MODULES = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"]

MODULE_FILES = {
    "M1": "M1_core_identity_context.json",
    "M2": "M2_preferences_values.json",
    "M3": "M3_purchase_decision_logic.json",
    "M4": "M4_lifestyle_grooming.json",
    "M5": "M5_sensory_aesthetic.json",
    "M6": "M6_bodywash_deep_dive.json",
    "M7": "M7_media_influence.json",
    "M8": "M8_concept_test.json",
}


def load_question_bank(module_id: str) -> dict:
    """Load a question bank JSON file."""
    with open(SEED_DATA_PATH / MODULE_FILES[module_id]) as f:
        return json.load(f)


def test_question_bank_files_exist():
    """Test that all required question bank files exist."""
    for module_id in REQUIRED_MODULES:
        filename = MODULE_FILES[module_id]
        assert (SEED_DATA_PATH / filename).exists(), f"Missing {filename}"


@pytest.mark.parametrize("module_id", REQUIRED_MODULES)
def test_question_bank_structure(module_id: str):
    """Test that question bank has required structure."""
    data = load_question_bank(module_id)

    # Required top-level fields
    assert "module_id" in data
    assert "module_name" in data
    assert "module_goal" in data
    assert "completion_criteria" in data
    assert "signal_targets" in data
    assert "questions" in data

    # Check module ID matches
    assert data["module_id"] == module_id


@pytest.mark.parametrize("module_id", REQUIRED_MODULES)
def test_question_bank_has_minimum_questions(module_id: str):
    """Test that each module has at least 10 questions."""
    data = load_question_bank(module_id)
    assert len(data["questions"]) >= 10, f"{module_id} should have at least 10 questions"


@pytest.mark.parametrize("module_id", REQUIRED_MODULES)
def test_question_format(module_id: str):
    """Test that each question has required fields."""
    data = load_question_bank(module_id)

    for q in data["questions"]:
        assert "question_id" in q
        assert "question_text" in q
        assert "question_type" in q
        assert "target_signals" in q
        assert "priority" in q
        assert "estimated_seconds" in q

        # Validate question type
        valid_types = [
            "open_text", "numeric", "single_select", "multi_select",
            "scale", "scale_open", "rank_order", "matrix_scale", "matrix_premium",
            "forced_choice", "scenario", "trade_off", "likert",
        ]
        assert q["question_type"] in valid_types, f"Invalid type: {q['question_type']}"


@pytest.mark.parametrize("module_id", REQUIRED_MODULES)
def test_question_bank_covers_signals(module_id: str):
    """Test that questions cover all target signals."""
    data = load_question_bank(module_id)
    target_signals = set(data["signal_targets"])
    covered_signals = set()

    for q in data["questions"]:
        covered_signals.update(q["target_signals"])

    # Check all target signals are covered
    missing = target_signals - covered_signals
    assert not missing, f"Missing coverage for signals: {missing}"


@pytest.mark.parametrize("module_id", REQUIRED_MODULES)
def test_completion_criteria(module_id: str):
    """Test that completion criteria are valid."""
    data = load_question_bank(module_id)
    criteria = data["completion_criteria"]

    assert "coverage_threshold" in criteria
    assert "confidence_threshold" in criteria
    assert "min_questions" in criteria

    # Thresholds should be between 0 and 1
    assert 0 <= criteria["coverage_threshold"] <= 1
    assert 0 <= criteria["confidence_threshold"] <= 1
    assert criteria["min_questions"] >= 1
