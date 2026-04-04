"""Load respondent data from the shared database instead of CSV files.

Creates the same respondent dict format that data_processing.py produces,
but sources data from:
- simulation_runs table (twin responses)
- interview_turns table (real participant M8 responses)
"""

import re
import json
from data_processing import (
    TWIN_QID_MAP,
    PI_MAP,
    LIKERT_MAP,
    CONCEPTS,
    identify_question,
    parse_answer,
)


def load_twin_respondents_from_db(simulation_runs: list[dict]) -> list[dict]:
    """Build respondent dicts from simulation run results stored in the DB.

    Each simulation_run dict should have:
      - twin_id or twin_external_id (str)
      - responses (list of response dicts from step5)

    Each response dict should have:
      - question_id (e.g. "M8_q05")
      - structured_answer or raw_answer
      - question_type (optional)
    """
    respondents = []

    for idx, sim in enumerate(simulation_runs):
        twin_id = sim.get("twin_external_id") or sim.get("twin_id", f"T{idx:02d}")
        # Extract participant number from twin_id (e.g. P01_T001 -> 01)
        try:
            p_num = int(twin_id.split("_")[0].replace("P", ""))
        except (ValueError, IndexError):
            p_num = idx + 1

        respondent = {
            "id": f"T{p_num:02d}",
            "source": "twin",
            "screening": {},
            "concepts": [{} for _ in range(5)],
            "ranking": [],
            "price_pi": None,
            "wtp": None,
        }

        responses = sim.get("responses", [])
        if not responses:
            respondents.append(respondent)
            continue

        for resp in responses:
            qid = resp.get("question_id", "")
            if qid not in TWIN_QID_MAP:
                continue

            concept_idx, metric = TWIN_QID_MAP[qid]

            # Get answer value — prefer structured, fall back to raw
            answer = resp.get("structured_answer")
            if answer is None:
                answer = resp.get("raw_answer", "")

            answer_str = str(answer).strip().lower() if answer is not None else ""

            # Comparative questions
            if concept_idx is None:
                if metric == "ranking":
                    respondent["ranking"] = _parse_ranking(answer)
                elif metric == "price_pi":
                    respondent["price_pi"] = PI_MAP.get(answer_str, _try_int(answer))
                elif metric == "wtp":
                    respondent["wtp"] = _try_int(answer)
                elif metric == "importance":
                    if isinstance(answer, dict):
                        respondent["screening"]["importance"] = answer
                    else:
                        try:
                            respondent["screening"]["importance"] = json.loads(str(answer))
                        except (json.JSONDecodeError, TypeError):
                            pass
                continue

            # Concept-specific questions
            if 0 <= concept_idx < 5:
                parsed = _parse_metric_value(metric, answer, answer_str)
                if parsed is not None:
                    respondent["concepts"][concept_idx][metric] = parsed

        respondents.append(respondent)

    return respondents


def load_real_respondents_from_db(participants_data: list[dict]) -> list[dict]:
    """Build respondent dicts from real participant M8 interview data.

    Each participant dict should have:
      - participant_id or external_id (str, e.g. "P01")
      - m8_turns (list of dicts with question_text, answer_text)

    The M8 turns are the interview turns from module M8, ordered by turn_index.
    """
    respondents = []

    for idx, p_data in enumerate(participants_data):
        pid = p_data.get("external_id") or p_data.get("participant_id", f"P{idx+1:02d}")
        try:
            p_num = int(pid.replace("P", ""))
        except ValueError:
            p_num = idx + 1

        respondent = {
            "id": f"R{p_num:02d}",
            "source": "real",
            "screening": {},
            "concepts": [{} for _ in range(5)],
            "ranking": [],
            "price_pi": None,
            "wtp": None,
        }

        concept_idx = -1
        m8_turns = p_data.get("m8_turns", [])

        for turn in m8_turns:
            q_text = turn.get("question_text", "")
            answer = turn.get("answer_text", "")
            if not q_text or not answer:
                continue

            metric = identify_question(q_text)

            # Track concept blocks using "interest" as sentinel
            if metric == "interest":
                concept_idx += 1
                if concept_idx < 5:
                    respondent["concepts"][concept_idx]["interest"] = parse_answer("interest", answer)
                continue

            # Screening (before first concept)
            if concept_idx < 0:
                if "how often" in q_text.lower():
                    respondent["screening"]["frequency"] = answer.strip()
                elif "brands" in q_text.lower():
                    respondent["screening"]["brands"] = answer.strip()
                elif "satisfied" in q_text.lower():
                    respondent["screening"]["satisfaction"] = answer.strip()
                continue

            # Comparative questions
            if metric == "ranking":
                respondent["ranking"] = parse_answer("ranking", answer)
                continue
            if metric == "price_pi":
                respondent["price_pi"] = parse_answer("price_pi", answer)
                continue
            if metric == "wtp":
                respondent["wtp"] = parse_answer("wtp", answer)
                continue
            if metric == "importance":
                respondent["screening"]["importance"] = parse_answer("importance", answer)
                continue

            # Concept-specific
            if 0 <= concept_idx < 5 and metric != "unknown":
                respondent["concepts"][concept_idx][metric] = parse_answer(metric, answer)

        respondents.append(respondent)

    return respondents


def _parse_metric_value(metric: str, answer, answer_str: str):
    """Parse a metric value from a simulation response."""
    if metric in ("pi", "price_pi"):
        if isinstance(answer, (int, float)):
            return int(answer)
        return PI_MAP.get(answer_str, _try_int(answer))

    if metric in ("uniqueness", "relevance", "believability", "brand_fit"):
        if isinstance(answer, (int, float)):
            return int(answer)
        return LIKERT_MAP.get(answer_str, _try_int(answer))

    if metric in ("interest", "routine_fit", "time_saving"):
        return _try_int(answer)

    if metric in ("appealing", "change"):
        return str(answer).strip() if answer else None

    if metric == "barriers":
        if isinstance(answer, list):
            return answer
        if isinstance(answer, str):
            if answer.startswith("["):
                try:
                    return json.loads(answer)
                except json.JSONDecodeError:
                    pass
            return [b.strip() for b in answer.split(",") if b.strip()]
        return []

    if metric == "characteristics":
        if isinstance(answer, dict):
            return answer
        try:
            return json.loads(str(answer))
        except (json.JSONDecodeError, TypeError):
            return {}

    return answer


def _parse_ranking(answer) -> list:
    """Parse ranking answer from various formats."""
    if isinstance(answer, list):
        return answer
    if isinstance(answer, str):
        try:
            return json.loads(answer)
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _try_int(val) -> int | None:
    """Try to parse an integer from various types."""
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        try:
            return int(re.sub(r'[^\d]', '', val))
        except (ValueError, TypeError):
            return None
    return None
