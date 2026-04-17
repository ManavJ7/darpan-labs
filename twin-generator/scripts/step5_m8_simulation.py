"""
Step 5 — M8 Concept Test Simulation (Standalone).

Hardcodes the M8 concept-test questionnaire (64 questions across 7 sections),
runs batched LLM inference for a specified digital twin, and exports results
as JSON, JSONL (LLM log), and structured CSV.

Usage:
    python scripts/step5_m8_simulation.py --twins P01_T001 --mode combined --batch-size 8
"""
import argparse
import asyncio
import csv
import json
import logging
import re
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    OUTPUT_DIR,
    PROMPTS_DIR,
    LLM_GENERATION_MODEL,
    LLM_TEMPERATURE_QUERY,
    STEP5_MAX_BATCH_SIZE,
    LLM_MAX_TOKENS_BATCH_SURVEY,
    STEP5_VECTOR_TOP_K_PER_QUERY,
    STEP5_SURVEY_SOURCE_WEIGHT,
)
from scripts.step4_inference import (
    retrieve_vector,
    format_vector_evidence,
    classify_query_domains,
    retrieve_kg,
    format_kg_evidence,
    build_twin_summary,
    get_chroma_collection,
    get_kg,
    get_chroma_collection_for,
    get_kg_for,
    get_profiles_for,
    get_pruned_twins_for,
)
from scripts.step4_vector_index import get_client, get_collection, EMBEDDING_FUNCTION, query_twin as vector_query_twin
from scripts.step4_kg_build import (
    extract_traits,
    build_graph,
    save_graph,
    load_graph,
    load_pruned_twins,
    GRAPH_PATH,
)
from scripts.llm_utils import call_llm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ===========================================================================
# M8 Concept Definitions
# ===========================================================================

M8_CONCEPTS = [
    {
        "concept_index": 1,
        "product_name": "Dove 60-Second Body Spray",
        "consumer_insight": (
            "I wish I could get properly clean when I'm rushing between activities. "
            "When I'm squeezing a shower between the gym and a meeting, I need to get "
            "clean fast but current body washes take forever to lather, scrub, and rinse off completely."
        ),
        "key_benefit": (
            "Get completely clean in just 60 seconds — no scrubbing, minimal rinsing, "
            "maximum speed for your busiest days."
        ),
        "how_it_works": (
            "Proven micellar cleansing technology from Dove's face care range dissolves dirt "
            "and oil on contact. 60-second active formula breaks down sweat and grime while you "
            "wait, rinses away easily. Aerosol spray format covers your body evenly in seconds — "
            "no time wasted building lather."
        ),
        "price": "Rs.199 for 100ml trial size, Rs.399 for 200ml regular size",
    },
    {
        "concept_index": 2,
        "product_name": "Dove Skip",
        "consumer_insight": (
            "I want to moisturize my skin after every shower, but I always forget or skip it "
            "because it's such a hassle. I wish there was a way to get soft, hydrated skin "
            "without having to add another step to my routine."
        ),
        "key_benefit": "Get 12-hour moisturized skin straight from the shower — no body lotion needed.",
        "how_it_works": (
            "Advanced lipid-lock technology deposits a moisture barrier on your skin while you wash, "
            "so hydration stays sealed in even after toweling off. Contains 3x more moisturizing cream "
            "than regular body wash. Proven effective even in harsh conditions like air conditioning "
            "and dry winter weather."
        ),
        "price": "Rs.349 for 300ml, Rs.599 for 600ml",
    },
    {
        "concept_index": 3,
        "product_name": "Dove Night Wash",
        "consumer_insight": (
            "I wish my night shower could feel truly different from my rushed morning routine. "
            "My evening shower is the only time that's completely mine, but I'm using the same "
            "energizing body wash that's meant to wake me up."
        ),
        "key_benefit": (
            "Transform your night shower into a calming ritual that helps you unwind and prepare for sleep."
        ),
        "how_it_works": (
            "Contains chamomile and slow-release lavender oils clinically shown to reduce stress hormones "
            "when absorbed through skin. Creates a richer, slower lather that encourages you to take your "
            "time. Warm, muted fragrance designed specifically for evening use."
        ),
        "price": "Rs.299 for 250ml, Rs.499 for 500ml",
    },
    {
        "concept_index": 4,
        "product_name": "Dove Yours & Mine",
        "consumer_insight": (
            "I love wearing my partner's clothes or using their products because their scent makes me "
            "feel close to them throughout the day. But there's no way for us to actually carry each "
            "other's essence with us in our daily routines."
        ),
        "key_benefit": (
            "Carry a subtle trace of each other's personalized scent throughout your day, keeping you "
            "connected even when apart."
        ),
        "how_it_works": (
            "Personalized fragrance quiz analyzes your scent preferences and creates custom formulas "
            "from Dove's library of 200+ fragrance compounds. Each partner receives a body wash "
            "inspired by the other's scent profile."
        ),
        "price": "Rs.799 for couples kit (2x200ml), Rs.999 for premium gift edition",
    },
    {
        "concept_index": 5,
        "product_name": "Dove Skin ID",
        "consumer_insight": (
            "I wish I could find a body wash that actually works for my specific skin needs. My skin "
            "is different on different parts of my body — oily in some areas, dry in others, with "
            "dark patches on my elbows."
        ),
        "key_benefit": "Get a body wash that's custom-made for your unique skin needs across your entire body.",
        "how_it_works": (
            "AI skin analysis technology examines your uploaded photo and personal responses to identify "
            "your specific skin needs across different body areas. Custom-blended with targeted active "
            "ingredients like niacinamide for uneven tone, salicylic acid for body acne, or ceramides "
            "for dryness."
        ),
        "price": "Rs.699 for first order (includes skin analysis), Rs.549 for refills, Rs.499 with quarterly subscription",
    },
]


# ===========================================================================
# Reusable option sets
# ===========================================================================

_PURCHASE_INTENT_OPTIONS = [
    {"value": "definitely_buy", "label": "Definitely would buy"},
    {"value": "probably_buy", "label": "Probably would buy"},
    {"value": "might_buy", "label": "Might or might not buy"},
    {"value": "probably_not", "label": "Probably would not buy"},
    {"value": "definitely_not", "label": "Definitely would not buy"},
]

_UNIQUENESS_OPTIONS = [
    {"value": "extremely", "label": "Extremely unique"},
    {"value": "very", "label": "Very unique"},
    {"value": "somewhat", "label": "Somewhat unique"},
    {"value": "not_very", "label": "Not very unique"},
    {"value": "not_at_all", "label": "Not at all unique"},
]

_RELEVANCE_OPTIONS = [
    {"value": "extremely", "label": "Extremely relevant"},
    {"value": "very", "label": "Very relevant"},
    {"value": "somewhat", "label": "Somewhat relevant"},
    {"value": "not_very", "label": "Not very relevant"},
    {"value": "not_at_all", "label": "Not at all relevant"},
]

_BELIEVABILITY_OPTIONS = [
    {"value": "completely", "label": "Completely believable"},
    {"value": "very", "label": "Very believable"},
    {"value": "somewhat", "label": "Somewhat believable"},
    {"value": "not_very", "label": "Not very believable"},
    {"value": "not_at_all", "label": "Not at all believable"},
]

_BRAND_FIT_OPTIONS = [
    {"value": "extremely", "label": "Fits extremely well"},
    {"value": "very", "label": "Fits very well"},
    {"value": "somewhat", "label": "Fits somewhat well"},
    {"value": "not_very", "label": "Doesn't fit very well"},
    {"value": "not_at_all", "label": "Doesn't fit at all"},
]

_MATRIX_PAIRS = ["Basic-Premium", "Boring-Exciting", "Not for me-Made for me", "Old-fashioned-Innovative", "Forgettable-Memorable"]

_CONCERN_OPTIONS = [
    {"value": "price_high", "label": "Price might be too high"},
    {"value": "skeptical_claims", "label": "Might not work as claimed"},
    {"value": "skin_irritation", "label": "Could irritate my skin"},
    {"value": "availability", "label": "Might not be available where I shop"},
    {"value": "distrust_new", "label": "Don't trust new products"},
    {"value": "happy_current", "label": "Happy with current product"},
    {"value": "other", "label": "Other concern"},
    {"value": "no_concerns", "label": "No concerns"},
]

_SCALE_1_5_INTEREST = {"min": 1, "max": 5, "anchors": {"1": "Not at all interested", "3": "Moderately interested", "5": "Extremely interested"}}
_SCALE_1_5_ROUTINE = {"min": 1, "max": 5, "anchors": {"1": "Not at all well", "3": "Somewhat well", "5": "Extremely well"}}
_SCALE_1_5_TIME = {"min": 1, "max": 5, "anchors": {"1": "Not at all likely", "3": "Moderately likely", "5": "Extremely likely"}}
_SCALE_1_5_MATRIX = {"min": 1, "max": 5, "anchors": {"1": "Strongly left word", "3": "Neutral", "5": "Strongly right word"}}
_SCALE_1_5_IMPORTANCE = {"min": 1, "max": 5, "anchors": {"1": "Not at all important", "3": "Moderately important", "5": "Extremely important"}}

_IMPORTANCE_FACTORS = [
    "Cleansing effectiveness",
    "Moisturization / skin hydration",
    "Fragrance / scent quality",
    "Gentleness on skin",
    "Value for money",
    "Innovation / uniqueness",
    "Brand trust and reputation",
    "Convenience / ease of use",
]

_CONCEPT_NAMES_FOR_RANK = [
    "Dove 60-Second Body Spray",
    "Dove Skip",
    "Dove Night Wash",
    "Dove Yours & Mine",
    "Dove Skin ID",
]


# ===========================================================================
# Helper to build concept question blocks
# ===========================================================================

def _concept_questions(concept_idx: int, concept_name: str, q_ids: dict) -> list[dict]:
    """Build the standard set of concept evaluation questions.

    q_ids is a dict mapping question role to its M8 question ID, e.g.:
        {
            "interest": "M8_q05", "appeal": "M8_q06", "improve": "M8_q07",
            "routine_fit": "M8_q08", "time_saving": "M8_q09", "purchase": "M8_q10",
            "uniqueness": "M8_q12", "relevance": "M8_q13", "believability": "M8_q14",
            "brand_fit": "M8_q15", "matrix": "M8_q16", "concerns": "M8_q19",
        }
    Keys may be absent (e.g. concept 3 has no time_saving).
    """
    section = f"concept{concept_idx}"
    qs = []

    if "interest" in q_ids:
        qs.append({
            "question_id": q_ids["interest"],
            "question_text": f"Overall, how interested are you in this product concept?",
            "question_type": "scale",
            "section": section,
            "concept_index": concept_idx,
            "options": None,
            "scale": _SCALE_1_5_INTEREST,
            "matrix_items": None,
        })
    if "appeal" in q_ids:
        qs.append({
            "question_id": q_ids["appeal"],
            "question_text": f"What, if anything, did you find most appealing about the {concept_name} concept?",
            "question_type": "open_text",
            "section": section,
            "concept_index": concept_idx,
            "options": None,
            "scale": None,
            "matrix_items": None,
        })
    if "improve" in q_ids:
        qs.append({
            "question_id": q_ids["improve"],
            "question_text": f"What, if anything, would you change or improve about the {concept_name} concept?",
            "question_type": "open_text",
            "section": section,
            "concept_index": concept_idx,
            "options": None,
            "scale": None,
            "matrix_items": None,
        })
    if "routine_fit" in q_ids:
        qs.append({
            "question_id": q_ids["routine_fit"],
            "question_text": f"How well does the {concept_name} concept fit with your current routine?",
            "question_type": "scale",
            "section": section,
            "concept_index": concept_idx,
            "options": None,
            "scale": _SCALE_1_5_ROUTINE,
            "matrix_items": None,
        })
    if "time_saving" in q_ids:
        qs.append({
            "question_id": q_ids["time_saving"],
            "question_text": f"How likely would the {concept_name} be to save you time in your routine?",
            "question_type": "scale",
            "section": section,
            "concept_index": concept_idx,
            "options": None,
            "scale": _SCALE_1_5_TIME,
            "matrix_items": None,
        })
    if "purchase" in q_ids:
        qs.append({
            "question_id": q_ids["purchase"],
            "question_text": f"Based on what you've seen, how likely would you be to buy the {concept_name}?",
            "question_type": "single_select",
            "section": section,
            "concept_index": concept_idx,
            "options": _PURCHASE_INTENT_OPTIONS,
            "scale": None,
            "matrix_items": None,
        })
    if "uniqueness" in q_ids:
        qs.append({
            "question_id": q_ids["uniqueness"],
            "question_text": f"How unique or different is the {concept_name} compared to other body wash products available today?",
            "question_type": "single_select",
            "section": section,
            "concept_index": concept_idx,
            "options": _UNIQUENESS_OPTIONS,
            "scale": None,
            "matrix_items": None,
        })
    if "relevance" in q_ids:
        qs.append({
            "question_id": q_ids["relevance"],
            "question_text": f"How relevant is the {concept_name} to your personal needs?",
            "question_type": "single_select",
            "section": section,
            "concept_index": concept_idx,
            "options": _RELEVANCE_OPTIONS,
            "scale": None,
            "matrix_items": None,
        })
    if "believability" in q_ids:
        qs.append({
            "question_id": q_ids["believability"],
            "question_text": f"How believable are the claims made about the {concept_name}?",
            "question_type": "single_select",
            "section": section,
            "concept_index": concept_idx,
            "options": _BELIEVABILITY_OPTIONS,
            "scale": None,
            "matrix_items": None,
        })
    if "brand_fit" in q_ids:
        qs.append({
            "question_id": q_ids["brand_fit"],
            "question_text": f"How well does the {concept_name} idea fit with what you expect from the Dove brand?",
            "question_type": "single_select",
            "section": section,
            "concept_index": concept_idx,
            "options": _BRAND_FIT_OPTIONS,
            "scale": None,
            "matrix_items": None,
        })
    if "matrix" in q_ids:
        qs.append({
            "question_id": q_ids["matrix"],
            "question_text": f"How would you describe the {concept_name}? Rate each pair of characteristics.",
            "question_type": "matrix_scale",
            "section": section,
            "concept_index": concept_idx,
            "options": None,
            "scale": _SCALE_1_5_MATRIX,
            "matrix_items": _MATRIX_PAIRS,
        })
    if "concerns" in q_ids:
        qs.append({
            "question_id": q_ids["concerns"],
            "question_text": f"What concerns, if any, would you have about trying the {concept_name}? Select all that apply.",
            "question_type": "multi_select",
            "section": section,
            "concept_index": concept_idx,
            "options": _CONCERN_OPTIONS,
            "scale": None,
            "matrix_items": None,
        })
    return qs


# ===========================================================================
# M8 Full Questionnaire
# ===========================================================================

def build_m8_questionnaire() -> list[dict]:
    """Return the complete M8 questionnaire as a list of question dicts."""
    questions: list[dict] = []

    # ---- Category Screening ----
    questions.append({
        "question_id": "M8_q01",
        "question_text": "How often do you personally use body wash or shower gel?",
        "question_type": "single_select",
        "section": "category_screening",
        "concept_index": None,
        "options": [
            {"value": "daily", "label": "Daily"},
            {"value": "several_weekly", "label": "Several times a week"},
            {"value": "once_weekly", "label": "About once a week"},
            {"value": "few_monthly", "label": "A few times a month"},
            {"value": "rarely_never", "label": "Rarely or never"},
        ],
        "scale": None,
        "matrix_items": None,
    })
    questions.append({
        "question_id": "M8_q02",
        "question_text": "Which body wash or shower gel brands have you used in the past 3 months? Select all that apply.",
        "question_type": "multi_select",
        "section": "category_screening",
        "concept_index": None,
        "options": [
            {"value": "dove", "label": "Dove"},
            {"value": "olay", "label": "Olay"},
            {"value": "nivea", "label": "Nivea"},
            {"value": "johnsons", "label": "Johnson's"},
            {"value": "lux", "label": "Lux"},
            {"value": "pears", "label": "Pears"},
            {"value": "fiama", "label": "Fiama"},
            {"value": "body_shop", "label": "The Body Shop"},
            {"value": "other", "label": "Other brand"},
            {"value": "dont_remember", "label": "Don't remember"},
        ],
        "scale": None,
        "matrix_items": None,
    })
    questions.append({
        "question_id": "M8_q03",
        "question_text": "Overall, how satisfied are you with the body wash or shower gel you currently use most often?",
        "question_type": "single_select",
        "section": "category_screening",
        "concept_index": None,
        "options": [
            {"value": "very_satisfied", "label": "Very satisfied"},
            {"value": "somewhat_satisfied", "label": "Somewhat satisfied"},
            {"value": "neutral", "label": "Neither satisfied nor dissatisfied"},
            {"value": "somewhat_dissatisfied", "label": "Somewhat dissatisfied"},
            {"value": "very_dissatisfied", "label": "Very dissatisfied"},
        ],
        "scale": None,
        "matrix_items": None,
    })
    questions.append({
        "question_id": "M8_q04",
        "question_text": "What, if anything, would you most like to see improved in body wash or shower gel products?",
        "question_type": "open_text",
        "section": "category_screening",
        "concept_index": None,
        "options": None,
        "scale": None,
        "matrix_items": None,
    })

    # ---- Concept 1: Dove 60-Second Body Spray (q05-q10, q12-q16, q19) ----
    questions.extend(_concept_questions(1, "Dove 60-Second Body Spray", {
        "interest": "M8_q05", "appeal": "M8_q06", "improve": "M8_q07",
        "routine_fit": "M8_q08", "time_saving": "M8_q09", "purchase": "M8_q10",
        "uniqueness": "M8_q12", "relevance": "M8_q13", "believability": "M8_q14",
        "brand_fit": "M8_q15", "matrix": "M8_q16", "concerns": "M8_q19",
    }))

    # ---- Concept 2: Dove Skip (q20-q25, q27-q31, q34) ----
    questions.extend(_concept_questions(2, "Dove Skip", {
        "interest": "M8_q20", "appeal": "M8_q21", "improve": "M8_q22",
        "routine_fit": "M8_q23", "time_saving": "M8_q24", "purchase": "M8_q25",
        "uniqueness": "M8_q27", "relevance": "M8_q28", "believability": "M8_q29",
        "brand_fit": "M8_q30", "matrix": "M8_q31", "concerns": "M8_q34",
    }))

    # ---- Concept 3: Dove Night Wash (q35-q38, q40, q42-q46, q49) ----
    questions.extend(_concept_questions(3, "Dove Night Wash", {
        "interest": "M8_q35", "appeal": "M8_q36", "improve": "M8_q37",
        "routine_fit": "M8_q38",
        # NO time_saving for concept 3
        "purchase": "M8_q40",
        "uniqueness": "M8_q42", "relevance": "M8_q43", "believability": "M8_q44",
        "brand_fit": "M8_q45", "matrix": "M8_q46", "concerns": "M8_q49",
    }))

    # ---- Concept 4: Dove Yours & Mine (q50-q52, q55, q57-q61, q64) ----
    questions.extend(_concept_questions(4, "Dove Yours & Mine", {
        "interest": "M8_q50", "appeal": "M8_q51", "improve": "M8_q52",
        # NO routine_fit or time_saving for concept 4
        "purchase": "M8_q55",
        "uniqueness": "M8_q57", "relevance": "M8_q58", "believability": "M8_q59",
        "brand_fit": "M8_q60", "matrix": "M8_q61", "concerns": "M8_q64",
    }))

    # ---- Concept 5: Dove Skin ID (q65-q68, q70, q72-q76, q79) ----
    questions.extend(_concept_questions(5, "Dove Skin ID", {
        "interest": "M8_q65", "appeal": "M8_q66", "improve": "M8_q67",
        "routine_fit": "M8_q68",
        # NO time_saving for concept 5
        "purchase": "M8_q70",
        "uniqueness": "M8_q72", "relevance": "M8_q73", "believability": "M8_q74",
        "brand_fit": "M8_q75", "matrix": "M8_q76", "concerns": "M8_q79",
    }))

    # ---- Comparative & Pricing ----
    questions.append({
        "question_id": "M8_q17",
        "question_text": "How important are each of these factors when choosing a body wash?",
        "question_type": "matrix_scale",
        "section": "comparative",
        "concept_index": None,
        "options": None,
        "scale": _SCALE_1_5_IMPORTANCE,
        "matrix_items": _IMPORTANCE_FACTORS,
    })
    questions.append({
        "question_id": "M8_q80",
        "question_text": "Now that you've seen all 5 concepts, please rank them from most to least appealing. Pick your top 3.",
        "question_type": "rank_order",
        "section": "comparative",
        "concept_index": None,
        "options": [{"value": name, "label": name} for name in _CONCEPT_NAMES_FOR_RANK],
        "scale": None,
        "matrix_items": None,
    })
    questions.append({
        "question_id": "M8_q81",
        "question_text": "Thinking about the concept you found most appealing — at the price shown, how likely would you be to buy it?",
        "question_type": "single_select",
        "section": "comparative",
        "concept_index": None,
        "options": _PURCHASE_INTENT_OPTIONS,
        "scale": None,
        "matrix_items": None,
    })
    questions.append({
        "question_id": "M8_q82",
        "question_text": "What would you expect to pay for your most preferred concept? (Enter amount in rupees)",
        "question_type": "numeric",
        "section": "comparative",
        "concept_index": None,
        "options": None,
        "scale": None,
        "matrix_items": None,
    })

    return questions


# ===========================================================================
# Question Formatting — natural-language query for evidence retrieval
# ===========================================================================

def _concept_stimulus_block(concept_idx: int, concepts: list[dict] | None = None) -> str:
    """Build a concept / creative territory stimulus card block for prompts.

    Supports two shapes:
    - M8 concept testing: product_name, consumer_insight, key_benefit, how_it_works,
      reasons_to_believe, price
    - Ad creative testing: territory_name, core_insight, big_idea, key_message,
      execution_sketch, tone_mood, target_emotion
    """
    source = concepts if concepts is not None else M8_CONCEPTS
    for c in source:
        if c.get("concept_index") != concept_idx:
            continue
        # Ad creative territory shape
        if c.get("territory_name"):
            lines = [f"--- CREATIVE TERRITORY CARD ---"]
            lines.append(f"Name: {c['territory_name']}")
            if c.get("core_insight"):
                lines.append(f"Core Insight: {c['core_insight']}")
            if c.get("big_idea"):
                lines.append(f"Big Idea: {c['big_idea']}")
            if c.get("key_message"):
                lines.append(f"Key Message / Tagline: {c['key_message']}")
            if c.get("execution_sketch"):
                lines.append(f"Execution Sketch: {c['execution_sketch']}")
            tones = c.get("tone_mood") or []
            if isinstance(tones, list) and tones:
                lines.append(f"Tone & Mood: {', '.join(tones)}")
            elif isinstance(tones, str) and tones:
                lines.append(f"Tone & Mood: {tones}")
            emotions = c.get("target_emotion") or []
            if isinstance(emotions, list) and emotions:
                lines.append(f"Target Emotion: {', '.join(emotions)}")
            lines.append("--- END TERRITORY ---\n")
            return "\n".join(lines) + "\n"
        # Concept testing shape
        lines = [f"--- CONCEPT STIMULUS CARD ---"]
        lines.append(f"Product: {c.get('product_name', '')}")
        if c.get("consumer_insight"):
            lines.append(f"Consumer Insight: {c['consumer_insight']}")
        if c.get("key_benefit"):
            lines.append(f"Key Benefit: {c['key_benefit']}")
        if c.get("how_it_works"):
            lines.append(f"How It Works: {c['how_it_works']}")
        if c.get("reasons_to_believe"):
            lines.append(f"Reasons to Believe: {c['reasons_to_believe']}")
        if c.get("price"):
            lines.append(f"Price: {c['price']}")
        lines.append("--- END STIMULUS ---\n")
        return "\n".join(lines) + "\n"
    return ""


def _concept_idx_for_question(q: dict) -> int | None:
    """Extract the concept/territory index this question is evaluating.

    Checks, in order:
    1. Explicit concept_index on the question (M8 hardcoded questionnaire)
    2. section name matching 'concept_N' or 'territory_N'
    3. Section name ending with '_N' (per-territory sections like M1_distinctiveness_1)
    """
    if q.get("concept_index") is not None:
        return q.get("concept_index")
    section = (q.get("section") or "").lower()
    if not section:
        return None
    m = re.search(r"(?:concept|territory)[_\s]*(\d+)", section)
    if m is None:
        m = re.search(r"_(\d+)$", section)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


# Module-level concepts override for format_question_query (set by run_simulation)
_active_concepts: list[dict] | None = None


def format_question_query(question: dict) -> str:
    """Format a survey question as a natural-language query for the inference engine."""
    # question_text may be a dict ({"en": ...}) or a plain string
    raw_qt = question.get("question_text", "")
    if isinstance(raw_qt, dict):
        q_text = raw_qt.get("en") or next(iter(raw_qt.values()), "")
    else:
        q_text = str(raw_qt)
    q_type = question.get("question_type", "open_text")
    concept_idx = _concept_idx_for_question(question)
    # options can be either a top-level field (M8 schema) or nested under scale.options (SDE schema)
    options = question.get("options") or (question.get("scale") or {}).get("options") or []
    scale = question.get("scale") or {}
    matrix_items = question.get("matrix_items") or []

    concept_block = _concept_stimulus_block(concept_idx, _active_concepts) if concept_idx is not None else ""

    option_labels = [o["label"] for o in options if isinstance(o, dict)]

    if q_type == "single_select":
        opts = ", ".join(option_labels) if option_labels else "the given options"
        return f"{concept_block}Survey question: {q_text}\nOptions: {opts}\nChoose exactly one option."

    if q_type == "multi_select":
        opts = ", ".join(option_labels) if option_labels else "the given options"
        return f"{concept_block}Survey question: {q_text}\nOptions: {opts}\nChoose all that apply."

    if q_type == "scale":
        anchors = scale.get("anchors", {})
        if anchors:
            anchor_desc = ", ".join(f"{k}={v}" for k, v in sorted(anchors.items(), key=lambda x: int(x[0])))
            return f"{concept_block}Survey question: {q_text}\nScale: {anchor_desc}\nGive a specific number."
        return f"{concept_block}Survey question: {q_text}\nRate on a scale of 1 to 5.\nGive a specific number."

    if q_type == "matrix_scale":
        anchors = scale.get("anchors", {})
        anchor_desc = ", ".join(f"{k}={v}" for k, v in sorted(anchors.items(), key=lambda x: int(x[0])))
        items_desc = ", ".join(matrix_items)
        return (
            f"{concept_block}Survey question: {q_text}\n"
            f"Items to rate: {items_desc}\n"
            f"Scale: {anchor_desc}\n"
            f"Give a number (1-5) for each item."
        )

    if q_type == "rank_order":
        opts = ", ".join(option_labels) if option_labels else "the given items"
        return f"{concept_block}Survey question: {q_text}\nChoices: {opts}\nRank your top 3 from most to least appealing."

    if q_type == "numeric":
        return f"{concept_block}Survey question: {q_text}\nProvide a numeric answer."

    # open_text
    return f"{concept_block}Survey question: {q_text}\nAnswer in 1-3 sentences."


# ===========================================================================
# Question Formatting — batch prompt block
# ===========================================================================

def format_questions_block(questions: list[dict]) -> str:
    """Format a batch of questions for the batch survey prompt."""
    lines = []
    for q in questions:
        q_id = q["question_id"]
        q_type = q.get("question_type", "open_text")
        # question_text may be a dict ({"en": ...}) or plain string
        raw_qt = q.get("question_text", "")
        if isinstance(raw_qt, dict):
            q_text = raw_qt.get("en") or next(iter(raw_qt.values()), "")
        else:
            q_text = str(raw_qt)
        concept_idx = _concept_idx_for_question(q)
        # options may be top-level (M8) or nested under scale.options (SDE)
        options = q.get("options") or (q.get("scale") or {}).get("options") or []
        scale = q.get("scale") or {}
        matrix_items = q.get("matrix_items") or []

        # Map our types to the prompt template types
        prompt_type = q_type
        if q_type == "scale":
            prompt_type = "rating"
        elif q_type == "matrix_scale":
            prompt_type = "rating"
        elif q_type == "rank_order":
            prompt_type = "ranking"
        elif q_type == "numeric":
            prompt_type = "open_text"

        lines.append(f"### {q_id} (type: {prompt_type})")

        # Concept / territory stimulus inline — uses active_concepts from run_simulation
        if concept_idx is not None:
            source = _active_concepts if _active_concepts is not None else M8_CONCEPTS
            for c in source:
                if c.get("concept_index") != concept_idx:
                    continue
                # Ad creative territory shape
                if c.get("territory_name"):
                    tones = c.get("tone_mood") or []
                    tones_str = ", ".join(tones) if isinstance(tones, list) else str(tones or "")
                    emotions = c.get("target_emotion") or []
                    emotions_str = ", ".join(emotions) if isinstance(emotions, list) else str(emotions or "")
                    bits = [f"  [Creative Territory #{concept_idx}: {c['territory_name']}"]
                    if c.get("core_insight"):
                        bits.append(f"    Insight: {c['core_insight']}")
                    if c.get("big_idea"):
                        bits.append(f"    Big idea: {c['big_idea']}")
                    if c.get("key_message"):
                        bits.append(f"    Key message: {c['key_message']}")
                    if c.get("execution_sketch"):
                        bits.append(f"    Execution: {c['execution_sketch']}")
                    if tones_str:
                        bits.append(f"    Tone: {tones_str}")
                    if emotions_str:
                        bits.append(f"    Target emotion: {emotions_str}")
                    bits[-1] = bits[-1] + "]"
                    lines.append("\n".join(bits))
                else:
                    # Concept testing shape (M8 + legacy)
                    lines.append(
                        f"  [Product Concept: {c.get('product_name', '')} — "
                        f"Insight: {(c.get('consumer_insight', '') or '')[:120]}; "
                        f"Benefit: {c.get('key_benefit', '')}; "
                        f"How It Works: {(c.get('how_it_works', '') or '')[:150]}; "
                        f"Price: {c.get('price', '')}]"
                    )
                break

        lines.append(f"Q: {q_text}")

        option_labels = [o["label"] for o in options if isinstance(o, dict) and "label" in o]

        if q_type == "single_select" and option_labels:
            lines.append(f"Options: {', '.join(option_labels)}")
            lines.append(f"Answer with EXACTLY one of the labels above (copy verbatim).")
        elif q_type == "multi_select" and option_labels:
            lines.append(f"Options (select all that apply): {', '.join(option_labels)}")
            lines.append(f"Answer with a JSON list of labels from above — every element MUST be copied verbatim from the options.")
        elif q_type in ("scale", "rating", "likert"):
            # Rating / likert questions — MUST render scale bounds in the prompt
            # or the LLM extrapolates to wider scales (e.g. returning 6 or 7 on a 1-5 likert).
            anchors = scale.get("anchors", {})
            scale_opts = scale.get("options") or options
            numeric_values = []
            for o in scale_opts:
                if isinstance(o, dict) and "value" in o:
                    try:
                        numeric_values.append(int(o["value"]))
                    except (TypeError, ValueError):
                        pass
            if numeric_values:
                scale_min, scale_max = min(numeric_values), max(numeric_values)
                # Attach label descriptions if present
                label_bits = []
                for o in scale_opts:
                    if isinstance(o, dict) and "label" in o and "value" in o:
                        label_bits.append(f"{o['value']}={o['label']}")
                label_str = ", ".join(label_bits) if label_bits else ""
                if label_str:
                    lines.append(f"Scale: {scale_min} to {scale_max} ({label_str})")
                else:
                    lines.append(f"Scale: {scale_min} to {scale_max}")
                lines.append(f"Answer with an INTEGER between {scale_min} and {scale_max} inclusive — no values outside this range.")
            elif anchors:
                anchor_desc = ", ".join(f"{k}={v}" for k, v in sorted(anchors.items(), key=lambda x: int(x[0])))
                anchor_keys = [int(k) for k in anchors.keys() if str(k).lstrip("-").isdigit()]
                if anchor_keys:
                    scale_min, scale_max = min(anchor_keys), max(anchor_keys)
                    lines.append(f"Scale: {anchor_desc}")
                    lines.append(f"Answer with an INTEGER between {scale_min} and {scale_max} inclusive.")
                else:
                    lines.append(f"Scale: {anchor_desc}")
        elif q_type == "matrix_scale":
            anchors = scale.get("anchors", {})
            if anchors:
                anchor_desc = ", ".join(f"{k}={v}" for k, v in sorted(anchors.items(), key=lambda x: int(x[0])))
                lines.append(f"Items: {', '.join(matrix_items)}")
                lines.append(f"Scale for each: {anchor_desc}")
                lines.append(f"Return a JSON object mapping each item to its score, e.g. {{{json.dumps({matrix_items[0]: 3, matrix_items[1]: 4})}}}.")
        elif q_type == "rank_order" and option_labels:
            lines.append(f"Rank from most to least preferred (top 3): {', '.join(option_labels)}")
        elif q_type == "numeric":
            lines.append("Provide a numeric value.")

        lines.append("")

    return "\n".join(lines)


def format_prior_answers_text(prior_answers: dict, questions_lookup: dict) -> str:
    """Format prior answers for inclusion in the batch prompt."""
    if not prior_answers:
        return "No earlier answers yet — this is the first batch."
    lines = []
    for q_id, answer in prior_answers.items():
        q = questions_lookup.get(q_id, {})
        q_text = q.get("question_text", q_id) if isinstance(q, dict) else q_id
        if isinstance(answer, (list, dict)):
            ans_str = json.dumps(answer)
        else:
            ans_str = str(answer)
        lines.append(f"- {q_id}: {q_text[:80]} -> {ans_str}")
    return "\n".join(lines)


# ===========================================================================
# Response Parsing
# ===========================================================================

def parse_batch_answer(answer_val, question: dict):
    """Parse a structured answer from the batch JSON response."""
    q_type = question["question_type"]
    options = question.get("options") or []
    scale = question.get("scale") or {}

    if q_type == "scale":
        if isinstance(answer_val, (int, float)):
            return int(answer_val)
        if isinstance(answer_val, str):
            nums = re.findall(r'\b(\d+)\b', answer_val)
            if nums:
                return int(nums[0])
        return answer_val

    if q_type == "matrix_scale":
        # Expect a dict mapping item -> score
        if isinstance(answer_val, dict):
            return {k: int(v) if isinstance(v, (int, float)) else v for k, v in answer_val.items()}
        return answer_val

    if q_type == "single_select":
        if isinstance(answer_val, str):
            # Try to match label -> value
            for o in options:
                if o["label"].lower() == answer_val.lower():
                    return o["value"]
            # Fuzzy match
            for o in options:
                if o["label"].lower() in answer_val.lower() or answer_val.lower() in o["label"].lower():
                    return o["value"]
            # Maybe they returned the value directly
            for o in options:
                if o["value"] == answer_val:
                    return answer_val
        return answer_val

    if q_type == "multi_select":
        if isinstance(answer_val, list):
            result = []
            for item in answer_val:
                matched = False
                for o in options:
                    if isinstance(item, str) and (o["label"].lower() == item.lower() or o["value"] == item):
                        result.append(o["value"])
                        matched = True
                        break
                if not matched:
                    result.append(item)
            return result
        return answer_val

    if q_type == "rank_order":
        if isinstance(answer_val, list):
            return answer_val
        return answer_val

    if q_type == "numeric":
        if isinstance(answer_val, (int, float)):
            return answer_val
        if isinstance(answer_val, str):
            nums = re.findall(r'[\d,]+', answer_val.replace(",", ""))
            if nums:
                try:
                    return int(nums[0])
                except ValueError:
                    return answer_val
        return answer_val

    # open_text
    return str(answer_val).strip() if answer_val else ""


# ===========================================================================
# Evidence Retrieval (batched)
# ===========================================================================

def retrieve_batch_evidence(
    twin_id: str,
    queries: list[str],
    top_k_per_query: int = STEP5_VECTOR_TOP_K_PER_QUERY,
    collection=None,
) -> tuple[str, dict]:
    """Retrieve and merge vector evidence for a batch of queries."""
    coll = collection or get_chroma_collection()
    all_vector_results = []
    seen = set()
    for query in queries:
        results = vector_query_twin(coll, query, twin_id=twin_id, top_k=top_k_per_query)
        for r in results:
            key = (r["question_text"], r["answer_text"])
            if key not in seen:
                seen.add(key)
                all_vector_results.append(r)

    all_vector_results.sort(key=lambda x: x["weighted_score"], reverse=True)
    all_vector_results = all_vector_results[:40]

    vector_evidence = format_vector_evidence(all_vector_results)
    stats = {"n_vector_evidence": len(all_vector_results)}
    return vector_evidence, stats


async def retrieve_batch_evidence_with_kg(
    twin_id: str,
    queries: list[str],
    mode: str,
    batch_id: int = 0,
    top_k_per_query: int = STEP5_VECTOR_TOP_K_PER_QUERY,
    collection=None,
    kg=None,
    participant_id: str = "default",
) -> tuple[str, dict]:
    """Full evidence retrieval including optional KG."""
    vector_evidence, stats = retrieve_batch_evidence(twin_id, queries, top_k_per_query, collection=collection)

    if mode in ("combined", "kg"):
        combined_query = " | ".join(queries)
        domains = await classify_query_domains(combined_query, kg=kg, participant_id=participant_id)

        kg_data = retrieve_kg(twin_id, domains, kg=kg)
        kg_evidence = format_kg_evidence(kg_data)
        evidence_block = f"{vector_evidence}\n---\n\n{kg_evidence}"
        stats["relevant_domains"] = domains
        stats["n_traits"] = len(kg_data["traits"])
    else:
        evidence_block = vector_evidence

    return evidence_block, stats


# ===========================================================================
# Batch Synthesis
# ===========================================================================

def _question_scale_bounds(q: dict) -> tuple[int, int] | None:
    """Return (min, max) integer bounds of a rating/likert question's scale, or None."""
    scale = q.get("scale") or {}
    scale_opts = scale.get("options") or q.get("options") or []
    numeric_values = []
    for o in scale_opts:
        if isinstance(o, dict) and "value" in o:
            try:
                numeric_values.append(int(o["value"]))
            except (TypeError, ValueError):
                pass
    if numeric_values:
        return min(numeric_values), max(numeric_values)
    # fall back to anchors
    anchors = scale.get("anchors") or {}
    anchor_keys = [int(k) for k in anchors.keys() if str(k).lstrip("-").isdigit()]
    if anchor_keys:
        return min(anchor_keys), max(anchor_keys)
    return None


def _option_labels_lower(q: dict) -> list[str]:
    """Return lower-cased option labels from either top-level options or scale.options."""
    options = q.get("options") or (q.get("scale") or {}).get("options") or []
    return [str(o["label"]).strip().lower() for o in options if isinstance(o, dict) and "label" in o]


def validate_batch_answers(batch: list[dict], batch_result: dict) -> list[dict]:
    """Return a list of {question_id, reason} for any answer that violates its question schema.

    Validates:
    - rating/scale/likert: integer within declared scale bounds
    - single_select: exact label match (case-insensitive)
    - multi_select / ranking: every element an exact label match
    Open_text and numeric are always accepted.
    """
    errors: list[dict] = []
    for q in batch:
        q_id = q["question_id"]
        q_type = q.get("question_type", "")

        if q_id not in batch_result:
            errors.append({"question_id": q_id, "reason": "missing from batch response"})
            continue

        entry = batch_result.get(q_id) or {}
        raw = entry.get("answer") if isinstance(entry, dict) else entry

        # --- rating / scale / likert: must be integer within scale bounds ---
        if q_type in ("rating", "scale", "likert", "likert_5"):
            try:
                val = int(raw) if not isinstance(raw, bool) else None
                if val is None:
                    raise ValueError
            except (TypeError, ValueError):
                errors.append({"question_id": q_id, "reason": f"rating answer {raw!r} is not an integer"})
                continue
            bounds = _question_scale_bounds(q)
            if bounds:
                lo, hi = bounds
                if not (lo <= val <= hi):
                    errors.append({"question_id": q_id, "reason": f"rating value {val} is outside scale {lo}-{hi}"})

        # --- single_select: label must match verbatim ---
        elif q_type == "single_select":
            labels = _option_labels_lower(q)
            if labels:
                if not isinstance(raw, str) or raw.strip().lower() not in labels:
                    errors.append({"question_id": q_id, "reason": f"single_select answer {raw!r} is not in options"})

        # --- multi_select / ranking: each element must match a label ---
        elif q_type in ("multi_select", "rank_order", "ranking"):
            labels = _option_labels_lower(q)
            if labels:
                if not isinstance(raw, list):
                    errors.append({"question_id": q_id, "reason": f"{q_type} answer must be a JSON list, got {type(raw).__name__}"})
                else:
                    for item in raw:
                        if not isinstance(item, str) or item.strip().lower() not in labels:
                            errors.append({"question_id": q_id, "reason": f"{q_type} item {item!r} is not a valid option"})
                            break

        # matrix_scale / open_text / numeric: no strict validation (matrix is complex, others free-form)

    return errors


def _format_validation_feedback(errors: list[dict]) -> str:
    """Render validator errors as a prompt-injectable corrective block."""
    if not errors:
        return ""
    lines = ["## RETRY — Your previous answers VIOLATED the rules below. Fix them now.",
             "For each listed question_id, re-read its Options / Scale line and return a compliant answer. Return the COMPLETE batch JSON again with corrected answers."]
    for e in errors[:20]:  # cap listing length for prompt size
        lines.append(f"- {e['question_id']}: {e['reason']}")
    if len(errors) > 20:
        lines.append(f"- ... plus {len(errors) - 20} more — re-check every answer against its scale/options before submitting.")
    return "\n".join(lines)


async def synthesize_batch(
    twin_id: str,
    evidence_block: str,
    questions_block: str,
    prior_answers_text: str,
    n_questions: int,
    batch_id: int = 0,
    participant_id: str = "default",
    product_brief_context: str = "",
    validation_feedback: list[dict] | None = None,
) -> dict:
    """Call LLM to answer a batch of survey questions.

    `product_brief_context` is injected into the prompt as per-study context
    (never written to persistent twin memory).

    `validation_feedback`, when non-empty, appends a corrective block listing
    which prior answers violated their schema — used by the retry loop in
    run_twin_batched to surface scale/option mismatches to the LLM.
    """
    prompt_template = (PROMPTS_DIR / "step5_batch_survey.txt").read_text()
    twin_summary = build_twin_summary(twin_id)

    pb_text = product_brief_context if (product_brief_context or "").strip() else "No product context for this study."

    prompt = (
        prompt_template
        .replace("{twin_summary}", twin_summary)
        .replace("{product_brief_context}", pb_text)
        .replace("{evidence_block}", evidence_block)
        .replace("{questions_block}", questions_block)
        .replace("{prior_survey_answers}", prior_answers_text)
    )

    feedback_block = _format_validation_feedback(validation_feedback or [])
    if feedback_block:
        prompt = f"{prompt}\n\n{feedback_block}\n"

    max_tokens = max(n_questions * 400, LLM_MAX_TOKENS_BATCH_SURVEY)

    result = await call_llm(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=LLM_TEMPERATURE_QUERY,
        model=LLM_GENERATION_MODEL,
        expect_json=True,
        participant_id=participant_id,
    )

    if isinstance(result, dict):
        return result
    return {}


# ===========================================================================
# Question Grouping
# ===========================================================================

def group_questions_into_batches(
    questions: list[dict],
    max_batch_size: int = STEP5_MAX_BATCH_SIZE,
) -> list[list[dict]]:
    """Group questions by type, then split into chunks, preserving survey order within each type."""
    by_type: dict[str, list[dict]] = {}
    for q in questions:
        qt = q["question_type"]
        by_type.setdefault(qt, []).append(q)

    batches = []
    for qt, group in by_type.items():
        for i in range(0, len(group), max_batch_size):
            batches.append(group[i:i + max_batch_size])

    return batches


# ===========================================================================
# Persistent Memory: ChromaDB
# ===========================================================================

def persist_answers_to_chromadb(twin_id: str, responses: list[dict], collection=None):
    """Write survey answers into ChromaDB for self-consistency."""
    collection = collection or get_chroma_collection()
    participant_id = twin_id.split("_")[0]

    ids = []
    documents = []
    metadatas = []

    for resp in responses:
        if resp.get("skipped") or not resp.get("raw_answer"):
            continue
        q_id = resp["question_id"]
        q_text = resp.get("question_text", "")
        raw = resp["raw_answer"] if isinstance(resp["raw_answer"], str) else json.dumps(resp["raw_answer"])
        doc_id = f"{twin_id}_m8survey_{q_id}"

        ids.append(doc_id)
        documents.append(f"{q_text} — {raw}")
        metadatas.append({
            "twin_id": twin_id,
            "participant_id": participant_id,
            "source": "survey",
            "module_id": "m8_concept_test",
            "weight": STEP5_SURVEY_SOURCE_WEIGHT,
            "question_text": q_text,
            "answer_text": raw[:500],
        })

    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(f"  Persisted {len(ids)} M8 survey answers to ChromaDB for {twin_id}")


# ===========================================================================
# Persistent Memory: Knowledge Graph
# ===========================================================================

async def persist_answers_to_kg(twin_id: str, all_responses: list[dict],
                               graph_path: Path | None = None, participant_id: str = "default"):
    """Extract new behavioral traits from survey answers and merge into KG (1 LLM call)."""
    graph_path = graph_path or GRAPH_PATH
    qa_pairs = []
    for resp in all_responses:
        if resp.get("skipped") or not resp.get("raw_answer"):
            continue
        raw = resp["raw_answer"] if isinstance(resp["raw_answer"], str) else json.dumps(resp["raw_answer"])
        qa_pairs.append({
            "question_text": resp.get("question_text", ""),
            "answer_text": raw,
            "source": "survey",
        })

    if not qa_pairs:
        logger.warning(f"No M8 survey answers to extract KG traits from for {twin_id}")
        return

    fake_twin = {"qa_pairs": qa_pairs}

    logger.info(f"Extracting KG traits from {len(qa_pairs)} M8 survey answers for {twin_id}...")
    try:
        new_traits = await extract_traits(twin_id, fake_twin, participant_id=participant_id)
    except Exception as e:
        logger.error(f"KG trait extraction failed for {twin_id}: {e}")
        return

    # extract_traits may return a list or a dict with "traits" key
    if isinstance(new_traits, list):
        new_traits = {"traits": new_traits}
    n_traits = len(new_traits.get("traits", []))
    logger.info(f"  Extracted {n_traits} new traits from M8 survey answers")

    try:
        if graph_path.exists():
            G = load_graph(graph_path)
        else:
            import networkx as nx
            G = nx.DiGraph()

        pruned_twins = load_pruned_twins(graph_path.parent)
        new_G = build_graph({twin_id: new_traits}, pruned_twins)

        for node, data in new_G.nodes(data=True):
            if not G.has_node(node):
                G.add_node(node, **data)
            else:
                if data.get("node_type") == "Trait":
                    G.add_node(node, **data)

        for u, v, data in new_G.edges(data=True):
            if not G.has_edge(u, v):
                G.add_edge(u, v, **data)

        save_graph(G, graph_path)
        logger.info(f"  Updated KG: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    except Exception as e:
        logger.error(f"Failed to merge M8 survey traits into KG: {e}")


# ===========================================================================
# Answer Label Resolution (for CSV)
# ===========================================================================

def resolve_answer_label(question: dict, structured_answer) -> str:
    """Resolve a structured answer value to a human-readable label for CSV."""
    q_type = question["question_type"]
    options = question.get("options") or []
    scale = question.get("scale") or {}
    matrix_items = question.get("matrix_items") or []

    if structured_answer is None:
        return ""

    if q_type == "open_text":
        return str(structured_answer)

    if q_type == "numeric":
        return str(structured_answer)

    if q_type == "scale":
        anchors = scale.get("anchors", {})
        val = str(structured_answer)
        if val in anchors:
            return f"{val} ({anchors[val]})"
        return val

    if q_type == "matrix_scale":
        if isinstance(structured_answer, dict):
            parts = []
            for item in matrix_items:
                score = structured_answer.get(item, "?")
                parts.append(f"{item}: {score}")
            return "; ".join(parts)
        return str(structured_answer)

    if q_type == "single_select":
        value_to_label = {o["value"]: o["label"] for o in options}
        if structured_answer in value_to_label:
            return value_to_label[structured_answer]
        return str(structured_answer)

    if q_type == "multi_select":
        if isinstance(structured_answer, list):
            value_to_label = {o["value"]: o["label"] for o in options}
            labels = [value_to_label.get(v, str(v)) for v in structured_answer]
            return "; ".join(labels)
        return str(structured_answer)

    if q_type == "rank_order":
        if isinstance(structured_answer, list):
            return " > ".join(str(item) for item in structured_answer)
        return str(structured_answer)

    return str(structured_answer)


def resolve_answer_value(question: dict, structured_answer) -> str:
    """Resolve a structured answer to a compact value string for CSV."""
    if structured_answer is None:
        return ""

    q_type = question["question_type"]

    if q_type == "matrix_scale":
        if isinstance(structured_answer, dict):
            return json.dumps(structured_answer)
        return str(structured_answer)

    if q_type == "multi_select":
        if isinstance(structured_answer, list):
            return json.dumps(structured_answer)
        return str(structured_answer)

    if q_type == "rank_order":
        if isinstance(structured_answer, list):
            return json.dumps(structured_answer)
        return str(structured_answer)

    return str(structured_answer)


# ===========================================================================
# Section Labels for CSV
# ===========================================================================

_SECTION_LABELS = {
    "category_screening": "Category Screening",
    "concept1": "Concept 1: Dove 60-Second Body Spray",
    "concept2": "Concept 2: Dove Skip",
    "concept3": "Concept 3: Dove Night Wash",
    "concept4": "Concept 4: Dove Yours & Mine",
    "concept5": "Concept 5: Dove Skin ID",
    "comparative": "Comparative & Pricing",
}


# ===========================================================================
# Export
# ===========================================================================

def export_json(twin_id: str, responses: list[dict], mode: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out = {
        "questionnaire": "M8 Concept Test",
        "twin_id": twin_id,
        "simulation_date": str(date.today()),
        "inference_mode": mode,
        "question_count": len(responses),
        "responses": responses,
    }
    path = output_dir / f"{twin_id}_m8_simulation_results.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    logger.info(f"JSON results saved to {path}")
    return path


def export_csv(twin_id: str, responses: list[dict], questions: list[dict], output_dir: Path) -> Path:
    """Export structured CSV: Section, Question ID, Question, Answer (Value), Answer (Label), Reasoning."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{twin_id}_m8_qa_responses.csv"

    q_lookup = {q["question_id"]: q for q in questions}
    resp_lookup = {r["question_id"]: r for r in responses}

    # Build ordered list: questions are already in survey order
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Section", "Question ID", "Question", "Answer (Value)", "Answer (Label)", "Reasoning"])

        for q in questions:
            q_id = q["question_id"]
            section_key = q["section"]
            section_label = _SECTION_LABELS.get(section_key, section_key)
            resp = resp_lookup.get(q_id, {})

            structured = resp.get("structured_answer")
            reasoning = resp.get("reasoning", "")

            answer_value = resolve_answer_value(q, structured)
            answer_label = resolve_answer_label(q, structured)

            writer.writerow([
                section_label,
                q_id,
                q["question_text"],
                answer_value,
                answer_label,
                reasoning,
            ])

    logger.info(f"CSV results saved to {path}")
    return path


# ===========================================================================
# Main Orchestration
# ===========================================================================

async def run_simulation(
    twin_id: str,
    questionnaire: list[dict],
    concepts: list[dict] | None = None,
    mode: str = "combined",
    batch_size: int = STEP5_MAX_BATCH_SIZE,
    output_dir: Path | None = None,
    participant_id: str = "default",
    collection=None,
    kg=None,
    product_brief: dict | None = None,
) -> list[dict]:
    """Run simulation for one twin with an arbitrary questionnaire.

    This is the general-purpose entry point used by the API/Celery tasks.
    The questionnaire is a list of question dicts (same schema as
    build_m8_questionnaire() output). Concepts are optional stimulus cards.

    `product_brief` is an optional dict injected into every batch's prompt as
    per-study context (ad_creative_testing). It is NEVER persisted to ChromaDB
    so it can't leak to future studies for the same twin.
    """
    global _active_concepts
    _active_concepts = concepts
    try:
        return await _run_simulation_inner(
            twin_id=twin_id,
            questions=questionnaire,
            mode=mode,
            batch_size=batch_size,
            output_dir=output_dir,
            participant_id=participant_id,
            collection=collection,
            kg=kg,
            product_brief=product_brief,
        )
    finally:
        _active_concepts = None


def _format_product_brief_for_prompt(product_brief: dict | None) -> str:
    """Format the Product Brief as a plain-text block for injection into the
    batch synthesis prompt. Ephemeral — never written to twin memory."""
    if not product_brief:
        return ""
    lines = []
    if product_brief.get("product_name"):
        lines.append(f"- **Product**: {product_brief['product_name']}")
    if product_brief.get("category"):
        lines.append(f"- **Category**: {product_brief['category']}")
    if product_brief.get("target_audience_description"):
        lines.append(f"- **Target audience**: {product_brief['target_audience_description']}")
    features = product_brief.get("key_features")
    if isinstance(features, list) and features:
        lines.append("- **Key features**: " + "; ".join(features))
    if product_brief.get("key_differentiator"):
        lines.append(f"- **Key differentiator**: {product_brief['key_differentiator']}")
    if product_brief.get("must_communicate"):
        lines.append(f"- **Must communicate**: {product_brief['must_communicate']}")
    if not lines:
        return ""
    return (
        "You are being asked to evaluate creative ideas for this product:\n"
        + "\n".join(lines)
    )


async def run_m8_simulation(
    twin_id: str,
    mode: str = "combined",
    batch_size: int = STEP5_MAX_BATCH_SIZE,
    output_dir: Path | None = None,
    participant_id: str = "default",
    collection=None,
    kg=None,
) -> list[dict]:
    """Run the complete M8 concept test simulation for one twin."""
    questions = build_m8_questionnaire()
    return await run_simulation(
        twin_id=twin_id,
        questionnaire=questions,
        concepts=M8_CONCEPTS,
        mode=mode,
        batch_size=batch_size,
        output_dir=output_dir,
        participant_id=participant_id,
        collection=collection,
        kg=kg,
    )


async def _run_simulation_inner(
    twin_id: str,
    questions: list[dict],
    mode: str = "combined",
    batch_size: int = STEP5_MAX_BATCH_SIZE,
    output_dir: Path | None = None,
    participant_id: str = "default",
    collection=None,
    kg=None,
    product_brief: dict | None = None,
) -> list[dict]:
    """Internal implementation shared by run_simulation and run_m8_simulation."""
    t0 = time.time()
    output_dir = output_dir or (OUTPUT_DIR / "step5_m8_simulation")
    output_dir.mkdir(parents=True, exist_ok=True)

    pid = participant_id if participant_id != "default" else twin_id.split("_")[0]

    # Build the product brief prompt context once per twin run (ephemeral, not persisted)
    product_brief_context = _format_product_brief_for_prompt(product_brief)

    logger.info(f"Questionnaire: {len(questions)} questions")
    logger.info(f"Twin: {twin_id} | Mode: {mode} | Batch size: {batch_size}")
    if product_brief_context:
        logger.info(f"  Product Brief context: {len(product_brief_context)} chars (prompt-only, not persisted)")

    questions_lookup = {q["question_id"]: q for q in questions}
    prior_answers: dict = {}
    all_responses: list[dict] = []
    batch_id = 0

    # Group questions into batches by type
    batches = group_questions_into_batches(questions, batch_size)
    logger.info(f"Grouped into {len(batches)} batches")

    for batch in batches:
        batch_id += 1
        batch_q_ids = [q["question_id"] for q in batch]
        batch_type = batch[0]["question_type"]
        logger.info(f"  Batch {batch_id}: {len(batch)} questions (type={batch_type}) — {batch_q_ids}")

        t_batch = time.time()

        # 1. Format queries for evidence retrieval
        queries = [format_question_query(q) for q in batch]

        # 2. Retrieve evidence
        evidence_block, stats = await retrieve_batch_evidence_with_kg(
            twin_id, queries, mode, batch_id,
            collection=collection, kg=kg, participant_id=pid,
        )

        # 3. Format questions block for batch prompt
        questions_block = format_questions_block(batch)

        # 4. Format prior answers summary
        prior_text = format_prior_answers_text(prior_answers, questions_lookup)

        # 5. Batch synthesis with validation-retry loop.
        # We re-call the LLM up to MAX_VALIDATION_RETRIES times, each time feeding back
        # the specific violations (e.g. "q_m1_1_1: rating value 7 is outside scale 1-5")
        # so the twin can correct those answers. Only answers that survive validation
        # are persisted to ChromaDB — anything still invalid at the end of the retry
        # budget is marked skipped=True so persist_answers_to_chromadb drops it.
        MAX_VALIDATION_RETRIES = 3
        batch_result: dict = {}
        validation_errors: list[dict] = []
        for attempt in range(MAX_VALIDATION_RETRIES + 1):
            try:
                batch_result = await synthesize_batch(
                    twin_id, evidence_block, questions_block, prior_text,
                    n_questions=len(batch), batch_id=batch_id,
                    participant_id=pid,
                    product_brief_context=product_brief_context,
                    validation_feedback=validation_errors if attempt > 0 else None,
                )
            except Exception as e:
                logger.error(f"  Batch synthesis failed (attempt {attempt + 1}): {e}")
                batch_result = {}
                break

            validation_errors = validate_batch_answers(batch, batch_result)
            if not validation_errors:
                if attempt > 0:
                    logger.info(f"  Batch {batch_id} validated after {attempt} retry(ies)")
                break

            if attempt < MAX_VALIDATION_RETRIES:
                preview = "; ".join(f"{e['question_id']}: {e['reason']}" for e in validation_errors[:3])
                logger.warning(
                    f"  Batch {batch_id} validation failed (attempt {attempt + 1}/{MAX_VALIDATION_RETRIES + 1}, "
                    f"{len(validation_errors)} bad): {preview}{' ...' if len(validation_errors) > 3 else ''}"
                )
            else:
                logger.error(
                    f"  Batch {batch_id} exhausted {MAX_VALIDATION_RETRIES} validation retries; "
                    f"{len(validation_errors)} answers will be marked skipped (not persisted)"
                )

        # Question IDs that are still invalid after the retry budget — these will be
        # forced to skipped=True so they're excluded from ChromaDB persistence below.
        invalid_qids = {e["question_id"] for e in validation_errors}

        batch_elapsed = time.time() - t_batch

        # 6. Parse each answer
        for q in batch:
            q_id = q["question_id"]
            q_text = q["question_text"]
            reasoning = ""

            if q_id in batch_result:
                entry = batch_result[q_id]
                raw_answer = entry.get("answer", "")
                reasoning = entry.get("reasoning", "")
                if isinstance(raw_answer, (list, dict)):
                    raw_text = json.dumps(raw_answer)
                else:
                    raw_text = str(raw_answer)
                structured = parse_batch_answer(raw_answer, q)
            else:
                logger.warning(f"  {q_id} missing from batch result, recording as unanswered")
                raw_text = ""
                structured = None

            # Force-skip any answer that still violates validation after retries.
            # This keeps polluted answers out of ChromaDB + the exported results.
            is_invalid = q_id in invalid_qids
            if is_invalid:
                logger.warning(f"  {q_id}: final answer {raw_text!r} still invalid; marking skipped")

            resp = {
                "question_id": q_id,
                "question_text": q_text,
                "question_type": q["question_type"],
                "section": q["section"],
                "concept_index": q.get("concept_index"),
                "raw_answer": raw_text,
                "structured_answer": structured if not is_invalid else None,
                "reasoning": reasoning,
                "skipped": structured is None or is_invalid,
                "invalid": is_invalid,
                "inference_mode": mode,
                "evidence_count": stats.get("n_vector_evidence", 0),
                "elapsed_s": round(batch_elapsed / len(batch), 2),
            }
            all_responses.append(resp)
            if structured is not None and not is_invalid:
                prior_answers[q_id] = structured

        # 7. Persist batch answers to ChromaDB for self-consistency — but only the
        # ones that passed validation (or were free-text / unskipped). The skipped
        # filter in persist_answers_to_chromadb already drops invalid answers since
        # we set skipped=True above for anything that exhausted retries.
        batch_responses = [r for r in all_responses[-len(batch):] if not r.get("skipped")]
        persist_answers_to_chromadb(twin_id, batch_responses, collection=collection)

        logger.info(f"  Batch {batch_id} complete: {batch_elapsed:.1f}s "
                     f"({stats.get('n_vector_evidence', 0)} vector, "
                     f"{stats.get('n_traits', 0)} KG traits)")

    # After all batches: persist to KG
    graph_path = (output_dir.parent / "step4_knowledge_graph.json") if output_dir else None
    await persist_answers_to_kg(twin_id, all_responses, graph_path=graph_path, participant_id=pid)

    # Export
    export_json(twin_id, all_responses, mode, output_dir)
    export_csv(twin_id, all_responses, questions, output_dir)

    total_elapsed = time.time() - t0
    answered = sum(1 for r in all_responses if not r.get("skipped"))
    logger.info(f"\nM8 simulation complete for {twin_id}")
    logger.info(f"  {answered}/{len(questions)} questions answered")
    logger.info(f"  Total time: {total_elapsed:.1f}s")
    logger.info(f"  Output dir: {output_dir}")

    return all_responses


# ===========================================================================
# CLI
# ===========================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="M8 Concept Test Simulation — standalone, hardcoded questionnaire"
    )
    parser.add_argument(
        "--twins", default="P01_T001",
        help="Twin ID to simulate (default: P01_T001)"
    )
    parser.add_argument(
        "--mode", choices=["vector", "kg", "combined"], default="combined",
        help="Inference mode (default: combined)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=STEP5_MAX_BATCH_SIZE,
        help=f"Questions per LLM batch call (default: {STEP5_MAX_BATCH_SIZE})"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Override output directory"
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else None

    await run_m8_simulation(
        twin_id=args.twins,
        mode=args.mode,
        batch_size=args.batch_size,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    asyncio.run(main())
