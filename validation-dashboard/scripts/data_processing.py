"""CSV parsing and question mapping for Dove concept validation data."""

import os
import csv
import json
import re
from pathlib import Path

CONCEPTS = [
    "Dove 60-Second Body Spray",
    "Dove Skip",
    "Dove Night Wash",
    "Dove Yours & Mine",
    "Dove Skin ID",
]

CONCEPT_SHORT = ["Body Spray", "Skip", "Night Wash", "Yours & Mine", "Skin ID"]

PI_MAP = {
    "definitely_buy": 5, "definitely buy": 5,
    "probably_buy": 4, "probably buy": 4, "probably would buy": 4,
    "might_buy": 3, "might buy": 3, "might or might not buy": 3,
    "probably_not": 2, "probably not": 2, "probably would not buy": 2,
    "definitely_not": 1, "definitely not": 1, "definitely would not buy": 1,
}

LIKERT_MAP = {
    "extremely": 5, "completely": 5,
    "very": 4,
    "somewhat": 3,
    "not_very": 2, "not very": 2,
    "not_at_all": 1, "not at all": 1,
}

# Twin Question ID → (concept_index 0-4, metric_name)
TWIN_QID_MAP = {
    # Concept 1: Body Spray
    "M8_q05": (0, "interest"), "M8_q06": (0, "appealing"), "M8_q07": (0, "change"),
    "M8_q08": (0, "routine_fit"), "M8_q09": (0, "time_saving"), "M8_q10": (0, "pi"),
    "M8_q12": (0, "uniqueness"), "M8_q13": (0, "relevance"), "M8_q14": (0, "believability"),
    "M8_q15": (0, "brand_fit"), "M8_q16": (0, "characteristics"), "M8_q19": (0, "barriers"),
    # Concept 2: Skip
    "M8_q20": (1, "interest"), "M8_q21": (1, "appealing"), "M8_q22": (1, "change"),
    "M8_q23": (1, "routine_fit"), "M8_q24": (1, "time_saving"), "M8_q25": (1, "pi"),
    "M8_q27": (1, "uniqueness"), "M8_q28": (1, "relevance"), "M8_q29": (1, "believability"),
    "M8_q30": (1, "brand_fit"), "M8_q31": (1, "characteristics"), "M8_q34": (1, "barriers"),
    # Concept 3: Night Wash
    "M8_q35": (2, "interest"), "M8_q36": (2, "appealing"), "M8_q37": (2, "change"),
    "M8_q38": (2, "routine_fit"), "M8_q40": (2, "pi"),
    "M8_q42": (2, "uniqueness"), "M8_q43": (2, "relevance"), "M8_q44": (2, "believability"),
    "M8_q45": (2, "brand_fit"), "M8_q46": (2, "characteristics"), "M8_q49": (2, "barriers"),
    # Concept 4: Yours & Mine
    "M8_q50": (3, "interest"), "M8_q51": (3, "appealing"), "M8_q52": (3, "change"),
    "M8_q55": (3, "pi"),
    "M8_q57": (3, "uniqueness"), "M8_q58": (3, "relevance"), "M8_q59": (3, "believability"),
    "M8_q60": (3, "brand_fit"), "M8_q61": (3, "characteristics"), "M8_q64": (3, "barriers"),
    # Concept 5: Skin ID
    "M8_q65": (4, "interest"), "M8_q66": (4, "appealing"), "M8_q67": (4, "change"),
    "M8_q68": (4, "routine_fit"), "M8_q70": (4, "pi"),
    "M8_q72": (4, "uniqueness"), "M8_q73": (4, "relevance"), "M8_q74": (4, "believability"),
    "M8_q75": (4, "brand_fit"), "M8_q76": (4, "characteristics"), "M8_q79": (4, "barriers"),
    # Comparative
    "M8_q17": (None, "importance"), "M8_q80": (None, "ranking"),
    "M8_q81": (None, "price_pi"), "M8_q82": (None, "wtp"),
}

# Question text patterns for real transcript parsing
QUESTION_PATTERNS = [
    ("interest", "how interested are you in this product concept"),
    ("appealing", "find most appealing"),
    ("change", "change or improve"),
    ("routine_fit", "fit with your current routine"),
    ("time_saving", "save you time"),
    ("price_pi", "at the price shown"),
    ("pi", "how likely would you be to buy"),
    ("uniqueness", "how unique or different"),
    ("relevance", "how relevant"),
    ("believability", "how believable"),
    ("brand_fit", "fit with what you expect from"),
    ("characteristics", "rate each pair"),
    ("importance", "how important are each of these factors"),
    ("barriers", "what concerns"),
    ("ranking", "rank them from most to least"),
    ("wtp", "expect to pay"),
]


def identify_question(question_text: str) -> str:
    """Match question text to metric name via substring patterns."""
    q_lower = question_text.lower()
    for metric, pattern in QUESTION_PATTERNS:
        if pattern in q_lower:
            return metric
    return "unknown"


def parse_answer(metric: str, answer_text: str) -> any:
    """Convert answer text to numeric or structured value based on metric type."""
    answer_clean = answer_text.strip().lower()

    if metric == "pi" or metric == "price_pi":
        return PI_MAP.get(answer_clean, None)

    if metric in ("uniqueness", "relevance", "believability", "brand_fit"):
        return LIKERT_MAP.get(answer_clean, None)

    if metric in ("interest", "routine_fit", "time_saving"):
        try:
            return int(answer_text.strip())
        except ValueError:
            return None

    if metric in ("appealing", "change"):
        return answer_text.strip()

    if metric == "barriers":
        # Parse comma-separated or JSON array
        if answer_text.strip().startswith("["):
            try:
                return json.loads(answer_text)
            except json.JSONDecodeError:
                pass
        barriers = [b.strip().lower() for b in answer_text.split(",")]
        return [b for b in barriers if b]

    if metric == "ranking":
        # Parse JSON array of concept selections
        try:
            return json.loads(answer_text)
        except json.JSONDecodeError:
            return []

    if metric == "characteristics" or metric == "importance":
        try:
            return json.loads(answer_text)
        except json.JSONDecodeError:
            return {}

    if metric == "wtp":
        try:
            return int(re.sub(r'[^\d]', '', answer_text))
        except (ValueError, TypeError):
            return None

    return answer_text


def load_real_transcripts(testing_dir: str) -> list:
    """Load and parse all real customer transcripts."""
    respondents = []

    for i in range(1, 18):
        filepath = os.path.join(testing_dir, f"test_transcript_{i}.csv")
        if not os.path.exists(filepath):
            print(f"  Warning: {filepath} not found, skipping")
            continue

        respondent = {
            "id": f"R{i:02d}",
            "source": "real",
            "screening": {},
            "concepts": [{} for _ in range(5)],
            "ranking": [],
            "price_pi": None,
            "wtp": None,
        }

        concept_idx = -1  # Start before first concept

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                q_text = row["question_text"]
                answer = row["answer_text"]
                metric = identify_question(q_text)

                # Track concept blocks using "interest" as sentinel
                if metric == "interest":
                    concept_idx += 1
                    if concept_idx < 5:
                        respondent["concepts"][concept_idx]["interest"] = parse_answer("interest", answer)
                    continue

                # Screening questions (before first concept)
                if concept_idx < 0:
                    if "how often" in q_text.lower():
                        respondent["screening"]["frequency"] = answer.strip()
                    elif "brands" in q_text.lower():
                        respondent["screening"]["brands"] = answer.strip()
                    elif "satisfied" in q_text.lower():
                        respondent["screening"]["satisfaction"] = answer.strip()
                    elif "improved" in q_text.lower():
                        respondent["screening"]["improvement"] = answer.strip()
                    continue

                # Comparative questions (after all 5 concepts)
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

                # Concept-specific questions
                if 0 <= concept_idx < 5 and metric != "unknown":
                    respondent["concepts"][concept_idx][metric] = parse_answer(metric, answer)

        respondents.append(respondent)

    return respondents


def load_twin_responses(responses_dir: str) -> list:
    """Load and parse all digital twin responses."""
    respondents = []

    # Discover twin CSV files dynamically
    import glob
    twin_files = sorted(glob.glob(os.path.join(responses_dir, "P*_m8_qa_responses.csv")))
    if not twin_files:
        # Fallback: try step5 naming pattern
        twin_files = sorted(glob.glob(os.path.join(responses_dir, "P*_T*_m8_qa_responses.csv")))

    for filepath in twin_files:
        basename = os.path.basename(filepath)
        # Extract participant number from filename (e.g., P01 from P01_m8_qa... or P01_T001_m8_qa...)
        pid = basename.split("_")[0]
        idx = int(pid[1:])

        respondent = {
            "id": f"T{idx:02d}",
            "source": "twin",
            "screening": {},
            "concepts": [{} for _ in range(5)],
            "ranking": [],
            "price_pi": None,
            "wtp": None,
        }

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                qid = row.get("Question ID", "").strip()
                answer_val = row.get("Answer (Value)", "").strip()
                answer_label = row.get("Answer (Label)", "").strip()

                if qid not in TWIN_QID_MAP:
                    continue

                concept_idx, metric = TWIN_QID_MAP[qid]

                # Comparative questions
                if concept_idx is None:
                    if metric == "ranking":
                        respondent["ranking"] = parse_ranking_twin(answer_val)
                    elif metric == "price_pi":
                        respondent["price_pi"] = parse_pi_twin(answer_val)
                    elif metric == "wtp":
                        try:
                            respondent["wtp"] = int(re.sub(r'[^\d]', '', answer_val))
                        except (ValueError, TypeError):
                            pass
                    elif metric == "importance":
                        respondent["screening"]["importance"] = parse_json_safe(answer_val)
                    continue

                # Concept-level questions
                if metric == "pi":
                    respondent["concepts"][concept_idx][metric] = parse_pi_twin(answer_val)
                elif metric in ("uniqueness", "relevance", "believability", "brand_fit"):
                    respondent["concepts"][concept_idx][metric] = parse_likert_twin(answer_val)
                elif metric in ("interest", "routine_fit", "time_saving"):
                    try:
                        respondent["concepts"][concept_idx][metric] = int(answer_val)
                    except (ValueError, TypeError):
                        pass
                elif metric in ("appealing", "change"):
                    respondent["concepts"][concept_idx][metric] = answer_val
                elif metric == "barriers":
                    respondent["concepts"][concept_idx][metric] = parse_barriers_twin(answer_val)
                elif metric == "characteristics":
                    respondent["concepts"][concept_idx][metric] = parse_json_safe(answer_val)
                else:
                    respondent["concepts"][concept_idx][metric] = answer_val

        respondents.append(respondent)

    return respondents


def parse_pi_twin(val: str) -> int | None:
    val_lower = val.strip().lower()
    if val_lower in PI_MAP:
        return PI_MAP[val_lower]
    # Try numeric
    try:
        v = int(val)
        if 1 <= v <= 5:
            return v
    except (ValueError, TypeError):
        pass
    return None


def parse_likert_twin(val: str) -> int | None:
    val_lower = val.strip().lower()
    if val_lower in LIKERT_MAP:
        return LIKERT_MAP[val_lower]
    try:
        v = int(val)
        if 1 <= v <= 5:
            return v
    except (ValueError, TypeError):
        pass
    return None


def parse_barriers_twin(val: str) -> list:
    if val.startswith("["):
        try:
            items = json.loads(val)
            return [b.strip().lower() for b in items if b.strip()]
        except json.JSONDecodeError:
            pass
    return [b.strip().lower() for b in val.split(",") if b.strip()]


def parse_ranking_twin(val: str) -> list:
    if val.startswith("["):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            pass
    return []


def parse_json_safe(val: str) -> dict:
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return {}


def load_all_data(base_dir: str) -> dict:
    """Load all data from both sources."""
    testing_dir = os.path.join(base_dir, "testing")
    # Use step5 simulation data if available, fallback to all_m8_responses
    step5_dir = os.path.join(base_dir, "step5_simulation_csvs")
    old_dir = os.path.join(base_dir, "all_m8_responses")
    responses_dir = step5_dir if os.path.isdir(step5_dir) else old_dir

    print("Loading real transcripts...")
    real = load_real_transcripts(testing_dir)
    print(f"  Loaded {len(real)} real respondents")

    print("Loading twin responses...")
    twins = load_twin_responses(responses_dir)
    print(f"  Loaded {len(twins)} twin respondents")

    return {"real": real, "twin": twins}
