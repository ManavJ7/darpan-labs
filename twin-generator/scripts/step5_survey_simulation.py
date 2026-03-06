"""
Step 5: Digital Twin Survey Simulation (Batched).

Fetches a locked questionnaire from the SDE API, runs questions through
the twin inference engine in batches (1 LLM call per 5-8 questions),
persists answers to ChromaDB + KG for self-consistency, and exports results.

Usage:
    # Batched mode (default) — 1 twin
    python scripts/step5_survey_simulation.py \\
      --study-id <UUID> \\
      --twins P01_T001 \\
      --mode combined --batch --batch-size 8

    # Legacy per-question mode
    python scripts/step5_survey_simulation.py \\
      --study-id <UUID> \\
      --twins P01_T001 \\
      --mode combined --no-batch

    # All P01 twins, vector-only
    python scripts/step5_survey_simulation.py \\
      --study-id <UUID> \\
      --twins P01_all \\
      --mode vector --batch
"""
import argparse
import asyncio
import copy
import csv
import json
import logging
import re
import sys
import time
from datetime import date
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    OUTPUT_DIR,
    PROMPTS_DIR,
    LLM_QUERY_MODEL,
    LLM_TEMPERATURE_QUERY,
    STEP5_MAX_BATCH_SIZE,
    LLM_MAX_TOKENS_BATCH_SURVEY,
    STEP5_VECTOR_TOP_K_PER_QUERY,
    STEP5_SURVEY_SOURCE_WEIGHT,
)
from scripts.step4_inference import (
    query_twin_inference,
    get_all_twin_ids,
    get_profiles,
    retrieve_vector,
    format_vector_evidence,
    classify_query_domains,
    retrieve_kg,
    format_kg_evidence,
    build_twin_summary,
    get_chroma_collection,
    get_kg,
)
from scripts.step4_vector_index import get_client, get_collection, EMBEDDING_FUNCTION
from scripts.step4_kg_build import extract_traits, build_graph, save_graph, load_graph, GRAPH_PATH
from scripts.llm_utils import call_llm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SDE_URL = "http://localhost:8001/api/v1"


# ---------------------------------------------------------------------------
# Questionnaire Fetching
# ---------------------------------------------------------------------------

async def fetch_questionnaire(study_id: str, sde_url: str) -> dict:
    """Fetch the simulation payload from SDE."""
    url = f"{sde_url}/studies/{study_id}/simulation-payload"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Questionnaire Expansion — expand concept-template sections per concept
# ---------------------------------------------------------------------------

CONCEPT_DEPENDENT_PREFIXES = ("S3_", "S4_", "S5_", "S7_")


def expand_questionnaire(questions: list[dict], concepts: list[dict]) -> list[dict]:
    """Expand concept-template questions into per-concept copies.

    The SDE questionnaire stores concept-dependent sections (S3, S4, S5, S7) as
    templates referencing a single concept. With N concepts, we clone each
    template question N times, producing unique question_ids and section names.

    Concept_exposure instruction questions (question_type == "concept_exposure")
    are skipped — they are display instructions, not answerable questions.

    Returns questions in survey order:
      S2 common → (S3+S4+S5+S7) for concept 1 → ... → concept N → S8 common
    """
    if not concepts:
        return questions

    # Collect all concept product_names for replacement
    concept_names = [c.get("product_name", "") for c in concepts]

    common = []
    concept_templates = []

    for q in questions:
        section = q.get("section", "")
        if any(section.startswith(prefix) for prefix in CONCEPT_DEPENDENT_PREFIXES):
            concept_templates.append(q)
        else:
            common.append(q)

    # Split common into before-concepts (S1, S2) and after-concepts (S8+)
    before = [q for q in common if not q.get("section", "").startswith("S8")]
    after = [q for q in common if q.get("section", "").startswith("S8")]

    expanded = list(before)

    # Detect duplicate question_ids across sections — use section prefix if needed
    from collections import Counter
    id_counts = Counter(t["question_id"] for t in concept_templates)
    has_dupes = any(v > 1 for v in id_counts.values())

    for concept_idx, concept in enumerate(concepts, 1):
        target_name = concept.get("product_name", "")
        for tmpl in concept_templates:
            # Skip concept_exposure instruction questions
            if tmpl.get("question_type") == "concept_exposure":
                continue

            q = copy.deepcopy(tmpl)

            # New question_id: disambiguate with section prefix if IDs are not unique
            base_id = tmpl["question_id"]
            if has_dupes and id_counts[base_id] > 1:
                section_short = tmpl.get("section", "").split("_")[0]  # e.g. "S3", "S4"
                base_id = f"{section_short}_{base_id}"
            q["question_id"] = f"{base_id}_C{concept_idx}"

            # New section: {original}_concept_{idx}
            q["section"] = f"{tmpl['section']}_concept_{concept_idx}"

            # Replace any hardcoded concept name in question_text
            q_text = q.get("question_text", {}).get("en", "")
            for name in concept_names:
                if name and name in q_text:
                    q_text = q_text.replace(name, target_name)
            if "question_text" in q and "en" in q["question_text"]:
                q["question_text"]["en"] = q_text

            expanded.append(q)

    expanded.extend(after)

    logger.info(
        f"Expanded questionnaire: {len(questions)} templates → {len(expanded)} questions "
        f"({len(concept_templates)} templates × {len(concepts)} concepts, "
        f"{len(before)} before, {len(after)} after)"
    )
    return expanded


# ---------------------------------------------------------------------------
# Question Formatting — convert structured question to natural-language query
# ---------------------------------------------------------------------------

def format_question_query(question: dict, concepts: list[dict] | None = None) -> str:
    """Format a survey question as a natural-language query for the inference engine."""
    q_text = question.get("question_text", {}).get("en", "")
    q_type = question.get("question_type", "open_text")
    scale = question.get("scale") or {}
    options = scale.get("options", [])
    anchors = scale.get("anchors", {})

    # Check if this is a concept-related question (section contains "concept")
    section = question.get("section", "").lower()
    is_concept_q = "concept" in section

    concept_block = ""
    if is_concept_q and concepts:
        idx_match = re.search(r"concept[_\s]*(\d+)", section)
        concept_idx = int(idx_match.group(1)) if idx_match else 1
        for c in concepts:
            if c.get("concept_index") == concept_idx:
                concept_block = (
                    f"You are shown this product concept:\n"
                    f"  Product: {c.get('product_name', '')}\n"
                    f"  Consumer Insight: {c.get('consumer_insight', '')}\n"
                    f"  Key Benefit: {c.get('key_benefit', '')}\n"
                    f"  Reasons to Believe: {c.get('reasons_to_believe', '')}\n\n"
                )
                break

    option_labels = [o.get("label", str(o.get("value", ""))) for o in options if isinstance(o, dict)]

    if q_type == "single_select":
        opts = ", ".join(option_labels) if option_labels else "the given options"
        query = f"{concept_block}Survey question: {q_text}\nOptions: {opts}\nChoose exactly one option and state your choice clearly."
    elif q_type == "multi_select":
        opts = ", ".join(option_labels) if option_labels else "the given options"
        query = f"{concept_block}Survey question: {q_text}\nOptions: {opts}\nChoose all that apply and list your selections."
    elif q_type in ("rating", "likert"):
        if anchors:
            anchor_desc = ", ".join(f"{k}={v}" for k, v in sorted(anchors.items()))
            query = f"{concept_block}Survey question: {q_text}\nRate on a scale where {anchor_desc}.\nGive a specific number."
        elif option_labels:
            query = f"{concept_block}Survey question: {q_text}\nOptions: {', '.join(option_labels)}\nGive a specific number."
        else:
            query = f"{concept_block}Survey question: {q_text}\nRate on a scale of 1 to 5.\nGive a specific number."
    elif q_type == "ranking":
        opts = ", ".join(option_labels) if option_labels else "the given items"
        query = f"{concept_block}Survey question: {q_text}\nRank these from most to least preferred: {opts}\nList them in order."
    else:
        # open_text or unknown
        query = f"{concept_block}Survey question: {q_text}\nAnswer in 1-3 sentences as you naturally would."

    return query


# ---------------------------------------------------------------------------
# Response Parsing — extract structured answers from free-text
# ---------------------------------------------------------------------------

def parse_response(raw_answer: str, question: dict) -> object:
    """Parse inference engine free-text into a structured answer."""
    q_type = question.get("question_type", "open_text")
    scale = question.get("scale") or {}
    options = scale.get("options", [])

    if q_type == "single_select":
        return _fuzzy_match_option(raw_answer, options)
    elif q_type == "multi_select":
        return _extract_multi_select(raw_answer, options)
    elif q_type in ("rating", "likert"):
        return _extract_rating(raw_answer, scale)
    elif q_type == "ranking":
        option_labels = [o.get("label", str(o.get("value", ""))) for o in options if isinstance(o, dict)]
        return _extract_ranking(raw_answer, option_labels)
    else:
        return raw_answer.strip()


def parse_batch_answer(answer_val, question: dict) -> object:
    """Parse a structured answer from the batch JSON response.

    Unlike parse_response (which parses free-text), the batch prompt already
    instructs the LLM to return typed values. We just need to validate/coerce.
    """
    q_type = question.get("question_type", "open_text")
    scale = question.get("scale") or {}
    options = scale.get("options", [])

    if q_type in ("rating", "likert"):
        if isinstance(answer_val, (int, float)):
            return int(answer_val) if answer_val == int(answer_val) else answer_val
        # Try to extract number from string
        if isinstance(answer_val, str):
            return _extract_rating(answer_val, scale)
        return answer_val

    if q_type == "single_select":
        if isinstance(answer_val, str):
            # Verify it's a valid option label
            option_labels = [o.get("label", str(o.get("value", ""))) for o in options if isinstance(o, dict)]
            if answer_val in option_labels:
                # Return the value, not the label
                for o in options:
                    if o.get("label") == answer_val:
                        return o.get("value", answer_val)
            # Fallback to fuzzy match
            return _fuzzy_match_option(answer_val, options)
        return answer_val

    if q_type == "multi_select":
        if isinstance(answer_val, list):
            return answer_val
        if isinstance(answer_val, str):
            return _extract_multi_select(answer_val, options)
        return answer_val

    if q_type == "ranking":
        if isinstance(answer_val, list):
            return answer_val
        if isinstance(answer_val, str):
            option_labels = [o.get("label", str(o.get("value", ""))) for o in options if isinstance(o, dict)]
            return _extract_ranking(answer_val, option_labels)
        return answer_val

    # open_text
    return str(answer_val).strip() if answer_val else ""


def _fuzzy_match_option(text: str, options: list[dict]) -> object:
    """Find the best matching option label in the text."""
    text_lower = text.lower()
    best_match = None
    best_len = 0
    for opt in options:
        label = opt.get("label", "")
        if label.lower() in text_lower and len(label) > best_len:
            best_match = opt.get("value", label)
            best_len = len(label)
    if best_match is not None:
        return best_match
    nums = re.findall(r'\b(\d+)\b', text)
    if nums:
        val = int(nums[0])
        for opt in options:
            if opt.get("value") == val:
                return val
    return options[0].get("value") if options else text.strip()


def _extract_multi_select(text: str, options: list[dict]) -> list:
    """Extract multiple matching options from text."""
    text_lower = text.lower()
    matched = []
    for opt in options:
        label = opt.get("label", "")
        if label.lower() in text_lower:
            matched.append(opt.get("value", label))
    return matched if matched else [options[0].get("value")] if options else []


def _extract_rating(text: str, scale: dict) -> object:
    """Extract a numeric rating from text."""
    nums = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
    if nums:
        anchors = scale.get("anchors", {})
        if anchors:
            valid_vals = [int(k) for k in anchors.keys() if k.isdigit()]
            min_v = min(valid_vals) if valid_vals else 1
            max_v = max(valid_vals) if valid_vals else 10
        else:
            options = scale.get("options", [])
            vals = [o.get("value") for o in options if isinstance(o, dict) and isinstance(o.get("value"), (int, float))]
            min_v = min(vals) if vals else 1
            max_v = max(vals) if vals else 5
        for n in nums:
            val = float(n)
            if min_v <= val <= max_v:
                return int(val) if val == int(val) else val
        return int(float(nums[0]))
    return None


def _extract_ranking(text: str, option_labels: list[str]) -> list[str]:
    """Extract an ordered ranking from text."""
    ranked = re.findall(r'\d+\.\s*(.+?)(?:\n|$)', text)
    if ranked:
        result = []
        for item in ranked:
            item_lower = item.strip().lower()
            for label in option_labels:
                if label.lower() in item_lower or item_lower in label.lower():
                    if label not in result:
                        result.append(label)
                    break
        return result if result else ranked

    positions = []
    text_lower = text.lower()
    for label in option_labels:
        pos = text_lower.find(label.lower())
        if pos >= 0:
            positions.append((pos, label))
    positions.sort()
    return [label for _, label in positions] if positions else option_labels


# ---------------------------------------------------------------------------
# show_if Evaluation
# ---------------------------------------------------------------------------

def evaluate_show_if(show_if: str | None, prior_answers: dict) -> bool:
    """Evaluate a simple show_if condition against prior answers."""
    if not show_if:
        return True

    show_if = show_if.strip()

    eq_match = re.match(r'(\w+)\s*==\s*(.+)', show_if)
    if eq_match:
        q_id, expected = eq_match.group(1), eq_match.group(2).strip().strip("'\"")
        actual = prior_answers.get(q_id)
        return str(actual) == expected

    neq_match = re.match(r'(\w+)\s*!=\s*(.+)', show_if)
    if neq_match:
        q_id, expected = neq_match.group(1), neq_match.group(2).strip().strip("'\"")
        actual = prior_answers.get(q_id)
        return str(actual) != expected

    in_match = re.match(r'(\w+)\s+in\s+\[(.+)\]', show_if)
    if in_match:
        q_id = in_match.group(1)
        values = [v.strip().strip("'\"") for v in in_match.group(2).split(",")]
        actual = prior_answers.get(q_id)
        return str(actual) in values

    logger.warning(f"Could not parse show_if: {show_if}")
    return True


def can_evaluate_show_if(show_if: str | None, prior_answers: dict) -> bool:
    """Check whether we have enough info to evaluate a show_if condition.

    Returns True if show_if is None/empty or if the referenced question_id
    already exists in prior_answers. Returns False if the referenced
    question hasn't been answered yet.
    """
    if not show_if:
        return True
    show_if = show_if.strip()

    # Extract the question_id referenced in the condition
    m = re.match(r'(\w+)\s*(?:==|!=|in\s)', show_if)
    if m:
        ref_q = m.group(1)
        return ref_q in prior_answers

    # Unknown pattern — assume evaluable
    return True


# ---------------------------------------------------------------------------
# Batched Evidence Retrieval
# ---------------------------------------------------------------------------

def retrieve_batch_evidence(
    twin_id: str,
    queries: list[str],
    mode: str,
    top_k_per_query: int = STEP5_VECTOR_TOP_K_PER_QUERY,
) -> tuple[str, dict]:
    """Retrieve and merge evidence for a batch of queries.

    All vector retrieval is local/fast. Returns (evidence_block, stats).
    Note: KG domain classification requires an LLM call — handled separately.
    """
    # Vector retrieval for each query (local, ~5ms each)
    all_vector_results = []
    seen = set()
    for query in queries:
        results = retrieve_vector(query, twin_id, top_k=top_k_per_query)
        for r in results:
            key = (r["question_text"], r["answer_text"])
            if key not in seen:
                seen.add(key)
                all_vector_results.append(r)

    # Sort by weighted score, cap at 40
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
    participant_id: str = "default",
) -> tuple[str, dict]:
    """Full evidence retrieval including optional KG (with LLM domain classification)."""
    vector_evidence, stats = retrieve_batch_evidence(twin_id, queries, mode, top_k_per_query)

    if mode in ("combined", "kg"):
        combined_query = " | ".join(queries)
        domains = await classify_query_domains(combined_query, participant_id=participant_id)

        kg_data = retrieve_kg(twin_id, domains)
        kg_evidence = format_kg_evidence(kg_data)
        evidence_block = f"{vector_evidence}\n---\n\n{kg_evidence}"
        stats["relevant_domains"] = domains
        stats["n_traits"] = len(kg_data["traits"])
    else:
        evidence_block = vector_evidence

    return evidence_block, stats


# ---------------------------------------------------------------------------
# Batch Question Formatting
# ---------------------------------------------------------------------------

def format_questions_block(questions: list[dict], concepts: list[dict] | None = None) -> str:
    """Format a batch of questions for the batch survey prompt."""
    lines = []
    for i, q in enumerate(questions, 1):
        q_id = q["question_id"]
        q_type = q.get("question_type", "open_text")
        q_text = q.get("question_text", {}).get("en", "")
        scale = q.get("scale") or {}
        options = scale.get("options", [])
        anchors = scale.get("anchors", {})

        # Concept block if applicable
        section = q.get("section", "").lower()
        concept_block = ""
        if "concept" in section and concepts:
            idx_match = re.search(r"concept[_\s]*(\d+)", section)
            concept_idx = int(idx_match.group(1)) if idx_match else 1
            for c in concepts:
                if c.get("concept_index") == concept_idx:
                    concept_block = (
                        f"  [Product Concept: {c.get('product_name', '')} — "
                        f"Insight: {c.get('consumer_insight', '')}; "
                        f"Benefit: {c.get('key_benefit', '')}; "
                        f"RTB: {c.get('reasons_to_believe', '')}]\n"
                    )
                    break

        lines.append(f"### {q_id} (type: {q_type})")
        if concept_block:
            lines.append(concept_block)
        lines.append(f"Q: {q_text}")

        option_labels = [o.get("label", str(o.get("value", ""))) for o in options if isinstance(o, dict)]
        if q_type == "single_select" and option_labels:
            lines.append(f"Options: {', '.join(option_labels)}")
        elif q_type == "multi_select" and option_labels:
            lines.append(f"Options (select all that apply): {', '.join(option_labels)}")
        elif q_type in ("rating", "likert"):
            if anchors:
                anchor_desc = ", ".join(f"{k}={v}" for k, v in sorted(anchors.items()))
                lines.append(f"Scale: {anchor_desc}")
            elif option_labels:
                lines.append(f"Scale options: {', '.join(option_labels)}")
            else:
                lines.append("Scale: 1 to 5")
        elif q_type == "ranking" and option_labels:
            lines.append(f"Rank from most to least preferred: {', '.join(option_labels)}")

        lines.append("")  # blank line between questions

    return "\n".join(lines)


def format_prior_answers_text(prior_answers: dict, questions_lookup: dict) -> str:
    """Format prior answers for inclusion in the batch prompt."""
    if not prior_answers:
        return "No earlier answers yet — this is the first batch."

    lines = []
    for q_id, answer in prior_answers.items():
        q = questions_lookup.get(q_id, {})
        q_text = q.get("question_text", {}).get("en", q_id) if isinstance(q, dict) else q_id
        if isinstance(answer, list):
            ans_str = ", ".join(str(a) for a in answer)
        else:
            ans_str = str(answer)
        lines.append(f"- {q_id}: {q_text[:80]} → {ans_str}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Batch Synthesis
# ---------------------------------------------------------------------------

async def synthesize_batch(
    twin_id: str,
    evidence_block: str,
    questions_block: str,
    prior_answers_text: str,
    n_questions: int,
    batch_id: int = 0,
    participant_id: str = "default",
) -> dict:
    """Call LLM to answer a batch of survey questions. Returns dict keyed by question_id."""
    prompt_template = (PROMPTS_DIR / "step5_batch_survey.txt").read_text()
    twin_summary = build_twin_summary(twin_id)

    prompt = (
        prompt_template
        .replace("{twin_summary}", twin_summary)
        .replace("{evidence_block}", evidence_block)
        .replace("{questions_block}", questions_block)
        .replace("{prior_survey_answers}", prior_answers_text)
    )

    max_tokens = max(n_questions * 300, LLM_MAX_TOKENS_BATCH_SURVEY)

    result = await call_llm(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=LLM_TEMPERATURE_QUERY,
        model=LLM_QUERY_MODEL,
        expect_json=True,
        participant_id=participant_id,
    )

    if isinstance(result, dict):
        return result
    return {}


# ---------------------------------------------------------------------------
# Question Grouping
# ---------------------------------------------------------------------------

def group_questions_into_batches(
    questions: list[dict],
    prior_answers: dict,
    max_batch_size: int = STEP5_MAX_BATCH_SIZE,
) -> tuple[list[list[dict]], list[dict]]:
    """Split questions into ready batches and deferred questions.

    Ready questions: no show_if, or show_if is evaluable from prior_answers.
    Deferred: show_if references a question not yet answered.

    Ready questions are grouped by question_type, then split into chunks
    of max_batch_size.
    """
    ready = []
    deferred = []

    for q in questions:
        show_if = q.get("show_if")
        if can_evaluate_show_if(show_if, prior_answers):
            # Check if actually visible
            if evaluate_show_if(show_if, prior_answers):
                ready.append(q)
            # else: skip-logic says hide — don't include in any batch
        else:
            deferred.append(q)

    # Group by question_type
    by_type: dict[str, list[dict]] = {}
    for q in ready:
        qt = q.get("question_type", "open_text")
        by_type.setdefault(qt, []).append(q)

    # Split into chunks of max_batch_size
    batches = []
    for qt, group in by_type.items():
        for i in range(0, len(group), max_batch_size):
            batches.append(group[i:i + max_batch_size])

    return batches, deferred


# ---------------------------------------------------------------------------
# Persistent Memory: ChromaDB
# ---------------------------------------------------------------------------

def persist_answers_to_chromadb(twin_id: str, responses: list[dict]):
    """Write survey answers into ChromaDB so later batches can retrieve them.

    Each answer is stored with source="survey" and weight=STEP5_SURVEY_SOURCE_WEIGHT.
    """
    collection = get_chroma_collection()
    participant_id = twin_id.split("_")[0]  # e.g. "P01" from "P01_T001"

    ids = []
    documents = []
    metadatas = []

    for resp in responses:
        if resp.get("skipped") or not resp.get("raw_answer"):
            continue
        q_id = resp["question_id"]
        q_text = resp.get("question_text", "")
        raw = resp["raw_answer"] if isinstance(resp["raw_answer"], str) else json.dumps(resp["raw_answer"])
        doc_id = f"{twin_id}_survey_{q_id}"

        ids.append(doc_id)
        documents.append(f"{q_text} — {raw}")
        metadatas.append({
            "twin_id": twin_id,
            "participant_id": participant_id,
            "source": "survey",
            "module_id": "",
            "weight": STEP5_SURVEY_SOURCE_WEIGHT,
            "question_text": q_text,
            "answer_text": raw[:500],  # cap metadata size
        })

    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(f"  Persisted {len(ids)} survey answers to ChromaDB for {twin_id}")


# ---------------------------------------------------------------------------
# Persistent Memory: Knowledge Graph
# ---------------------------------------------------------------------------

async def persist_answers_to_kg(twin_id: str, all_responses: list[dict], participant_id: str = "default"):
    """Extract new behavioral traits from survey answers and merge into KG."""
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
        logger.warning(f"No survey answers to extract KG traits from for {twin_id}")
        return

    fake_twin = {"qa_pairs": qa_pairs}

    logger.info(f"Extracting KG traits from {len(qa_pairs)} survey answers for {twin_id}...")
    try:
        new_traits = await extract_traits(twin_id, fake_twin, participant_id=participant_id)
    except Exception as e:
        logger.error(f"KG trait extraction failed for {twin_id}: {e}")
        return

    n_traits = len(new_traits.get("traits", []))
    logger.info(f"  Extracted {n_traits} new traits from survey answers")

    try:
        if GRAPH_PATH.exists():
            G = load_graph(GRAPH_PATH)
        else:
            G = __import__("networkx").DiGraph()

        from scripts.step4_kg_build import load_pruned_twins
        pruned_twins = load_pruned_twins()

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

        save_graph(G, GRAPH_PATH)
        logger.info(f"  Updated KG: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    except Exception as e:
        logger.error(f"Failed to merge survey traits into KG: {e}")


# ---------------------------------------------------------------------------
# Batched Orchestration (per twin)
# ---------------------------------------------------------------------------

async def run_twin_batched(
    twin_id: str,
    questions: list[dict],
    concepts: list[dict],
    mode: str,
    max_batch_size: int,
    output_dir: Path,
    participant_id: str = "default",
) -> list[dict]:
    """Run all survey questions for one twin using batched inference."""
    prior_answers: dict = {}
    all_responses: list[dict] = []
    questions_lookup = {q["question_id"]: q for q in questions}
    remaining = list(questions)
    batch_id = 0

    while remaining:
        batches, deferred = group_questions_into_batches(remaining, prior_answers, max_batch_size)

        if not batches:
            # All remaining are unresolvable (show_if depends on unanswered Qs)
            for q in deferred:
                all_responses.append({
                    "question_id": q["question_id"],
                    "question_text": q.get("question_text", {}).get("en", ""),
                    "question_type": q.get("question_type", ""),
                    "raw_answer": None,
                    "structured_answer": None,
                    "skipped": True,
                    "skip_reason": "unresolvable_show_if",
                    "inference_mode": mode,
                    "evidence_count": 0,
                    "elapsed_s": 0.0,
                })
            break

        for batch in batches:
            batch_id += 1
            batch_q_ids = [q["question_id"] for q in batch]
            logger.info(f"  Batch {batch_id}: {len(batch)} questions ({batch[0].get('question_type', '?')}) — {batch_q_ids}")

            t0 = time.time()

            # 1. Format queries for evidence retrieval
            queries = [format_question_query(q, concepts) for q in batch]

            # 2. Retrieve evidence (local vector + optional KG with 1 LLM call)
            evidence_block, stats = await retrieve_batch_evidence_with_kg(
                twin_id, queries, mode, batch_id,
                participant_id=participant_id,
            )

            # 3. Format questions block for batch prompt
            questions_block = format_questions_block(batch, concepts)

            # 4. Format prior answers summary
            prior_text = format_prior_answers_text(prior_answers, questions_lookup)

            # 5. Batch synthesis — 1 LLM call
            try:
                batch_result = await synthesize_batch(
                    twin_id, evidence_block, questions_block, prior_text,
                    n_questions=len(batch), batch_id=batch_id,
                    participant_id=participant_id,
                )
            except Exception as e:
                logger.error(f"  Batch synthesis failed: {e}. Falling back to individual queries.")
                batch_result = {}

            batch_elapsed = time.time() - t0

            # 6. Parse each answer
            for q_idx_in_batch, q in enumerate(batch):
                q_id = q["question_id"]
                q_text = q.get("question_text", {}).get("en", "")
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
                    # Fallback: individual query for this question
                    logger.warning(f"  {q_id} missing from batch result, falling back to individual query")
                    try:
                        fb_result = await query_twin_inference(twin_id, queries[q_idx_in_batch], mode=mode)
                        raw_text = fb_result.get("answer", "")
                        structured = parse_response(raw_text, q)
                    except Exception as fb_e:
                        logger.error(f"  Fallback also failed for {q_id}: {fb_e}")
                        raw_text = f"ERROR: {fb_e}"
                        structured = None

                resp = {
                    "question_id": q_id,
                    "question_text": q_text,
                    "question_type": q.get("question_type", ""),
                    "raw_answer": raw_text,
                    "structured_answer": structured,
                    "reasoning": reasoning,
                    "skipped": False,
                    "inference_mode": mode,
                    "evidence_count": stats.get("n_vector_evidence", 0),
                    "elapsed_s": round(batch_elapsed / len(batch), 2),
                }
                all_responses.append(resp)
                prior_answers[q_id] = structured

            # 7. Persist batch answers to ChromaDB
            batch_responses = [r for r in all_responses[-len(batch):] if not r.get("skipped")]
            persist_answers_to_chromadb(twin_id, batch_responses)

        remaining = deferred  # re-evaluate with updated prior_answers

    # After all batches: persist to KG (1 Opus call)
    await persist_answers_to_kg(twin_id, all_responses, participant_id=participant_id)

    return all_responses


# ---------------------------------------------------------------------------
# Legacy per-question orchestration (--no-batch)
# ---------------------------------------------------------------------------

async def run_twin_sequential(
    twin_id: str,
    questions: list[dict],
    concepts: list[dict],
    mode: str,
) -> list[dict]:
    """Original per-question simulation (1 LLM call per question)."""
    twin_responses = []
    prior_answers = {}

    for q_idx, question in enumerate(questions):
        q_id = question["question_id"]

        if not evaluate_show_if(question.get("show_if"), prior_answers):
            twin_responses.append({
                "question_id": q_id,
                "question_text": question.get("question_text", {}).get("en", ""),
                "question_type": question.get("question_type", ""),
                "raw_answer": None,
                "structured_answer": None,
                "skipped": True,
                "inference_mode": mode,
                "evidence_count": 0,
                "elapsed_s": 0.0,
            })
            continue

        query = format_question_query(question, concepts)

        try:
            result = await query_twin_inference(twin_id, query, mode=mode)
        except Exception as e:
            logger.error(f"  Inference failed for {twin_id}/{q_id}: {e}")
            twin_responses.append({
                "question_id": q_id,
                "question_text": question.get("question_text", {}).get("en", ""),
                "question_type": question.get("question_type", ""),
                "raw_answer": f"ERROR: {e}",
                "structured_answer": None,
                "skipped": False,
                "inference_mode": mode,
                "evidence_count": 0,
                "elapsed_s": 0.0,
            })
            continue

        structured = parse_response(result.get("answer", ""), question)

        twin_responses.append({
            "question_id": q_id,
            "question_text": question.get("question_text", {}).get("en", ""),
            "question_type": question.get("question_type", ""),
            "raw_answer": result.get("answer", ""),
            "structured_answer": structured,
            "skipped": False,
            "inference_mode": mode,
            "evidence_count": result.get("n_vector_evidence", result.get("n_evidence", 0)),
            "elapsed_s": result.get("elapsed_s", 0.0),
        })
        prior_answers[q_id] = structured

    return twin_responses


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_json(results: list[dict], payload: dict, mode: str, output_dir: Path) -> Path:
    """Export simulation results as JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out = {
        "study_id": payload.get("study_id", ""),
        "study_title": payload.get("study_title", ""),
        "simulation_date": str(date.today()),
        "inference_mode": mode,
        "twin_count": len(results),
        "question_count": len(results[0]["responses"]) if results else 0,
        "results": results,
    }
    path = output_dir / "step5_simulation_results.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    logger.info(f"JSON results saved to {path}")
    return path


def export_csv(results: list[dict], payload: dict, output_dir: Path) -> Path:
    """Export simulation results as CSV (wide format)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "step5_simulation_results.csv"

    if not results:
        return path

    q_ids = [r["question_id"] for r in results[0]["responses"]]

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        header = ["twin_id", "participant_id", "coherence_score"]
        for qid in q_ids:
            header.extend([qid, f"{qid}_raw"])
        writer.writerow(header)

        for twin in results:
            row = [
                twin.get("twin_id", ""),
                twin.get("participant_id", ""),
                twin.get("coherence_score", ""),
            ]
            resp_map = {r["question_id"]: r for r in twin.get("responses", [])}
            for qid in q_ids:
                r = resp_map.get(qid, {})
                row.append(r.get("structured_answer", ""))
                row.append(r.get("raw_answer", ""))
            writer.writerow(row)

    logger.info(f"CSV results saved to {path}")
    return path


# ---------------------------------------------------------------------------
# Upload results to SDE
# ---------------------------------------------------------------------------

async def upload_results(study_id: str, results: list[dict], payload: dict, mode: str, sde_url: str):
    """POST results back to SDE for frontend display."""
    upload_data = {
        "study_id": study_id,
        "study_title": payload.get("study_title", ""),
        "simulation_date": str(date.today()),
        "inference_mode": mode,
        "twin_count": len(results),
        "question_count": len(results[0]["responses"]) if results else 0,
        "results": results,
    }
    url = f"{sde_url}/studies/{study_id}/simulation-results"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=upload_data)
            resp.raise_for_status()
            logger.info(f"Results uploaded to SDE: {resp.json().get('id', '?')}")
    except Exception as e:
        logger.warning(f"Failed to upload results to SDE (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def run_simulation(
    study_id: str,
    twin_ids: list[str],
    mode: str = "combined",
    sde_url: str = DEFAULT_SDE_URL,
    output_dir: Path | None = None,
    upload: bool = True,
    batch: bool = True,
    batch_size: int = STEP5_MAX_BATCH_SIZE,
) -> list[dict]:
    """Run the full survey simulation pipeline."""
    t0 = time.time()
    output_dir = output_dir or (OUTPUT_DIR / "step5_simulation")

    # 1. Fetch questionnaire
    logger.info(f"Fetching questionnaire for study {study_id}...")
    payload = await fetch_questionnaire(study_id, sde_url)
    questions = payload.get("questions", [])
    concepts = payload.get("concepts", [])
    logger.info(f"Loaded {len(questions)} template questions, {len(concepts)} concepts")

    # Expand concept-dependent sections across all concepts
    questions = expand_questionnaire(questions, concepts)

    logger.info(f"Mode: {mode}, Batch: {batch}, Batch size: {batch_size}")

    # 2. Get twin profiles for metadata
    profiles = get_profiles()

    # 3. Run each twin through the questionnaire
    all_results = []
    for i, twin_id in enumerate(twin_ids):
        logger.info(f"[{i+1}/{len(twin_ids)}] Simulating {twin_id}...")
        twin_t0 = time.time()
        twin_profile = profiles.get(twin_id, {})

        if batch:
            twin_responses = await run_twin_batched(
                twin_id, questions, concepts, mode, batch_size, output_dir,
            )
        else:
            twin_responses = await run_twin_sequential(
                twin_id, questions, concepts, mode,
            )

        twin_elapsed = time.time() - twin_t0
        all_results.append({
            "twin_id": twin_id,
            "participant_id": twin_profile.get("participant_id", ""),
            "coherence_score": twin_profile.get("coherence_score"),
            "responses": twin_responses,
        })
        n_answered = sum(1 for r in twin_responses if not r.get("skipped"))
        logger.info(f"  {twin_id} done: {n_answered}/{len(twin_responses)} answered in {twin_elapsed:.1f}s")

    # 4. Export
    export_json(all_results, payload, mode, output_dir)
    export_csv(all_results, payload, output_dir)

    # 5. Upload to SDE
    if upload:
        await upload_results(study_id, all_results, payload, mode, sde_url)

    total_elapsed = time.time() - t0
    logger.info(f"Simulation complete: {len(twin_ids)} twins, {len(questions)} questions in {total_elapsed:.1f}s")
    return all_results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def resolve_twin_ids(twins_arg: str) -> list[str]:
    """Parse --twins argument into a list of twin IDs."""
    if twins_arg.lower() == "p01_all":
        all_ids = get_all_twin_ids()
        return [t for t in all_ids if t.startswith("P01_")]
    elif twins_arg.lower() == "all":
        return get_all_twin_ids()
    else:
        return [t.strip() for t in twins_arg.split(",")]


async def main():
    parser = argparse.ArgumentParser(description="Digital Twin Survey Simulation (Step 5)")
    parser.add_argument("--study-id", required=True, help="SDE study UUID")
    parser.add_argument("--twins", required=True,
                        help="Twin IDs: P01_T001,P01_T005 or P01_all or all")
    parser.add_argument("--mode", choices=["vector", "kg", "combined"], default="combined",
                        help="Inference mode (default: combined)")
    parser.add_argument("--sde-url", default=DEFAULT_SDE_URL,
                        help=f"SDE API base URL (default: {DEFAULT_SDE_URL})")
    parser.add_argument("--output", default=None,
                        help="Output directory (default: data/output/step5_simulation)")
    parser.add_argument("--no-upload", action="store_true",
                        help="Skip uploading results to SDE")

    # Batching options
    batch_group = parser.add_mutually_exclusive_group()
    batch_group.add_argument("--batch", action="store_true", default=True,
                             help="Use batched inference (default)")
    batch_group.add_argument("--no-batch", action="store_true",
                             help="Use legacy per-question inference")
    parser.add_argument("--batch-size", type=int, default=STEP5_MAX_BATCH_SIZE,
                        help=f"Questions per batch (default: {STEP5_MAX_BATCH_SIZE})")

    args = parser.parse_args()

    twin_ids = resolve_twin_ids(args.twins)
    logger.info(f"Resolved {len(twin_ids)} twins: {', '.join(twin_ids[:5])}{'...' if len(twin_ids) > 5 else ''}")

    output_dir = Path(args.output) if args.output else None
    use_batch = not args.no_batch

    results = await run_simulation(
        study_id=args.study_id,
        twin_ids=twin_ids,
        mode=args.mode,
        sde_url=args.sde_url,
        output_dir=output_dir,
        upload=not args.no_upload,
        batch=use_batch,
        batch_size=args.batch_size,
    )

    # Print summary
    print(f"\n{'='*60}")
    print(f"SIMULATION SUMMARY")
    print(f"{'='*60}")
    print(f"Twins: {len(results)}")
    if results:
        n_q = len(results[0]["responses"])
        n_skipped = sum(1 for r in results[0]["responses"] if r.get("skipped"))
        print(f"Questions: {n_q} ({n_skipped} skipped)")
    print(f"Mode: {args.mode}")
    print(f"Batched: {use_batch}" + (f" (size={args.batch_size})" if use_batch else ""))
    for r in results[:3]:
        answered = sum(1 for resp in r["responses"] if not resp.get("skipped"))
        print(f"  {r['twin_id']}: {answered} answered, coherence={r.get('coherence_score', '?')}")
    if len(results) > 3:
        print(f"  ... and {len(results) - 3} more twins")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
